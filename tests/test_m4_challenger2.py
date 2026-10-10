#!/usr/bin/env python3
"""
FSP IT-Talent Platform — Adversarial Verification Suite (Challenger M4-2)
Milestone 4: ATS Webhooks, Replay Tolerance, Exponential Retries, DLQ Lifecycle,
and Section 6 Quality Gate Execution.

Python 3.12+ Standard Library Only.
"""

import sys
import os
import json
import time
import hmac
import hashlib
import uuid
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


# ==============================================================================
# 1. ATS WEBHOOK SIGNATURE & REPLAY ENGINE (SPEC SECTION 5.4)
# ==============================================================================

def generate_fsp_signature(payload_json: str, secret: str, timestamp: int) -> str:
    """Computes X-FSP-Signature: t={timestamp},v1={hmac_sha256}."""
    signed_payload = f"{timestamp}.{payload_json}"
    sig = hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={sig}"


def verify_fsp_signature(
    payload_json: str,
    header_val: Optional[str],
    secret: str,
    current_time: int,
    max_drift_seconds: int = 300,
    allow_header_whitespace: bool = True
) -> Tuple[bool, str]:
    """
    Verifies X-FSP-Signature header against payload and replay tolerance window.
    Returns (is_valid, reason).
    """
    if not header_val or not isinstance(header_val, str):
        return False, "ERR_MISSING_OR_EMPTY_SIGNATURE_HEADER"
    if not secret:
        return False, "ERR_EMPTY_SECRET"

    try:
        parts: Dict[str, str] = {}
        for item in header_val.split(","):
            if "=" not in item:
                continue
            k, v = item.split("=", 1)
            k = k.strip().lower() if allow_header_whitespace else k.lower()
            v = v.strip() if allow_header_whitespace else v
            parts[k] = v
        
        if "t" not in parts or "v1" not in parts:
            return False, "ERR_MALFORMED_HEADER_PARTS"
        
        t = int(parts["t"])
        v1 = parts["v1"]
    except ValueError:
        return False, "ERR_INVALID_TIMESTAMP_FORMAT"
    except Exception as e:
        return False, f"ERR_PARSE_HEADER_EXCEPTION: {str(e)}"

    # Timestamp cannot be negative (pre-epoch)
    if t < 0:
        return False, "ERR_NEGATIVE_TIMESTAMP"

    # Replay attack tolerance check: |current_time - t| <= max_drift_seconds
    drift = current_time - t
    if abs(drift) > max_drift_seconds:
        return False, f"ERR_TIMESTAMP_DRIFT_EXCEEDED (drift={drift}s, max={max_drift_seconds}s)"

    # HMAC-SHA256 verification
    signed_payload = f"{t}.{payload_json}"
    expected_sig = hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(v1.lower(), expected_sig.lower()):
        return False, "ERR_SIGNATURE_MISMATCH"

    return True, "OK"


# ==============================================================================
# 2. WEBHOOK DELIVERY REPLAY CACHE (IDEMPOTENCY / DEDUPLICATION)
# ==============================================================================

class WebhookDeliveryReplayCache:
    """
    Simulates ATS receiver-side delivery idempotency cache to reject replayed
    requests within the 300s validity window.
    """
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self.seen_deliveries: Dict[str, int] = {}  # delivery_id -> received_at

    def process_delivery(
        self,
        delivery_id: str,
        payload_json: str,
        header_val: str,
        secret: str,
        current_time: int
    ) -> Tuple[int, str]:
        # Clean up expired items
        self.seen_deliveries = {
            d_id: ts for d_id, ts in self.seen_deliveries.items()
            if current_time - ts <= self.ttl_seconds
        }

        # 1. Signature & Replay Drift Check
        is_valid, reason = verify_fsp_signature(payload_json, header_val, secret, current_time, self.ttl_seconds)
        if not is_valid:
            if "DRIFT" in reason or "SIGNATURE" in reason or "NEGATIVE" in reason:
                return 401, reason
            return 400, reason

        # 2. Deduplication Check
        if delivery_id in self.seen_deliveries:
            return 409, "ERR_DUPLICATE_DELIVERY_REPLAY_DETECTED"

        # Record delivery
        self.seen_deliveries[delivery_id] = current_time
        return 200, "DELIVERED"


# ==============================================================================
# 3. EXPONENTIAL RETRY & DLQ LIFECYCLE SIMULATOR
# ==============================================================================

SCHEDULE_INTERVALS = [60, 300, 900, 3600, 86400]  # 1m, 5m, 15m, 1h, 24h


class WebhookDeliveryDispatcher:
    """
    Simulates FSP Platform Webhook dispatch lifecycle with exponential backoff
    and Dead-Letter Queue (DLQ).
    """
    def __init__(self, intervals: List[int] = SCHEDULE_INTERVALS):
        self.intervals = intervals

    def evaluate_delivery_attempt(
        self,
        consecutive_failures: int,
        http_status: Optional[int],
        network_error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Determines next state and retry delay based on HTTP status / network error.
        HTTP 2xx -> delivered
        HTTP 4xx -> rejected_by_receiver (non-retryable fatal error)
        HTTP 5xx / network error -> retryable via backoff schedule up to 5 retries, then dead_letter
        """
        if http_status is not None and 200 <= http_status < 300:
            return {
                "status": "delivered",
                "attempt": consecutive_failures,
                "delay_seconds": None,
                "retryable": False
            }

        # Non-retryable client errors (4xx)
        if http_status is not None and 400 <= http_status < 500:
            return {
                "status": "rejected_by_receiver",
                "attempt": consecutive_failures,
                "delay_seconds": None,
                "retryable": False,
                "error": f"Fatal client error HTTP {http_status}"
            }

        # Retryable errors (5xx or network drops)
        new_failure_count = consecutive_failures + 1
        if consecutive_failures < len(self.intervals):
            delay = self.intervals[consecutive_failures]
            return {
                "status": "retry_pending",
                "attempt": new_failure_count,
                "delay_seconds": delay,
                "retryable": True,
                "error": network_error or f"Server error HTTP {http_status}"
            }
        else:
            return {
                "status": "dead_letter",
                "attempt": consecutive_failures,
                "delay_seconds": None,
                "retryable": False,
                "error": "Exhausted all retry attempts"
            }


# ==============================================================================
# 4. ADVERSARIAL STRESS TEST CASES
# ==============================================================================

def test_hmac_signature_correctness_and_variations():
    """Stress tests HMAC-SHA256 signature calculation across various payloads."""
    print(">>> [TEST 1] HMAC-SHA256 Signature Robustness & Adversarial Tampering...")

    secret = "fsp_webhook_secret_key_prod_99812736"
    now = 1775419200

    # 1.1 Canonical payload
    payload = json.dumps({"event": "invitation.accepted", "candidate_id": 1042}, separators=(",", ":"))
    sig_header = generate_fsp_signature(payload, secret, now)
    ok, reason = verify_fsp_signature(payload, sig_header, secret, now)
    assert ok is True, f"Failed canonical verification: {reason}"

    # 1.2 UTF-8 Cyrillic characters in payload
    cyrillic_payload = json.dumps({
        "event": "application.created",
        "candidate": "Алексей Сергеевич Ковалев",
        "notes": "Специалист по распределенным системам и KITE тестированию — ЛЦТ 2026"
    }, ensure_ascii=False)
    sig_cyrillic = generate_fsp_signature(cyrillic_payload, secret, now)
    ok, reason = verify_fsp_signature(cyrillic_payload, sig_cyrillic, secret, now)
    assert ok is True, f"Failed Cyrillic UTF-8 payload verification: {reason}"

    # 1.3 Payload tampering: single character altered
    tampered_payload = cyrillic_payload.replace("Алексей", "Алексеи")
    ok, reason = verify_fsp_signature(tampered_payload, sig_cyrillic, secret, now)
    assert ok is False, "Tampered payload was incorrectly accepted!"
    assert reason == "ERR_SIGNATURE_MISMATCH"

    # 1.4 Whitespace alteration in JSON body
    whitespace_payload = json.dumps({
        "event": "invitation.accepted",
        "candidate_id": 1042
    }, indent=2)
    ok, reason = verify_fsp_signature(whitespace_payload, sig_header, secret, now)
    assert ok is False, "Raw body with altered whitespace should fail HMAC verification"

    # 1.5 Corrupted signature hash
    parts = sig_header.split(",")
    corrupted_header = f"{parts[0]},v1=deadbeef{parts[1][11:]}"
    ok, reason = verify_fsp_signature(payload, corrupted_header, secret, now)
    assert ok is False, "Corrupted signature hash was accepted!"
    assert reason == "ERR_SIGNATURE_MISMATCH"

    # 1.6 Wrong secret key
    ok, reason = verify_fsp_signature(payload, sig_header, "attacker_wrong_secret_123", now)
    assert ok is False, "Wrong secret was accepted!"
    assert reason == "ERR_SIGNATURE_MISMATCH"

    # 1.7 Empty secret key
    ok, reason = verify_fsp_signature(payload, sig_header, "", now)
    assert ok is False, "Empty secret was accepted!"

    # 1.8 Uppercase hex signature (verify constant-time case insensitivity)
    upper_header = f"{parts[0]},{parts[1].upper()}"
    ok, reason = verify_fsp_signature(payload, upper_header, secret, now)
    assert ok is True, "Uppercase hex should be safely accepted via case-insensitive compare"

    # 1.9 Large payload (> 150 KB)
    large_dict = {
        "event": "ats.export",
        "candidate_id": 9999,
        "resume_dump": "A" * 150000
    }
    large_payload = json.dumps(large_dict)
    sig_large = generate_fsp_signature(large_payload, secret, now)
    ok, reason = verify_fsp_signature(large_payload, sig_large, secret, now)
    assert ok is True, f"Large payload verification failed: {reason}"

    # 1.10 Header parsing variations
    # Space after comma: 't=123, v1=abc'
    spaced_header = f"{parts[0]}, {parts[1]}"
    ok, reason = verify_fsp_signature(payload, spaced_header, secret, now, allow_header_whitespace=True)
    assert ok is True, "Header with space after comma should parse with allow_header_whitespace=True"

    # Inverted order: 'v1=abc,t=123'
    inverted_header = f"{parts[1]},{parts[0]}"
    ok, reason = verify_fsp_signature(payload, inverted_header, secret, now)
    assert ok is True, "Header with inverted parameters should parse correctly"

    # Malformed headers
    for bad_header in [
        None,
        "",
        "garbage_value",
        "t=123",  # missing v1
        "v1=abc",  # missing t
        "t=not_a_number,v1=abc",  # non-numeric t
        "t=123.45,v1=abc",  # float timestamp
        "t=-100,v1=abc"  # negative timestamp
    ]:
        ok, reason = verify_fsp_signature(payload, bad_header, secret, now)
        assert ok is False, f"Malformed header '{bad_header}' was not rejected! Reason: {reason}"

    print("[PASS] Test 1: HMAC-SHA256 signature robustness & tampering rejection verified.")


def test_replay_attack_tolerance_boundaries():
    """Stress tests timestamp drift tolerance window (|current_time - t| <= 300s)."""
    print(">>> [TEST 2] Replay Attack Tolerance & Timestamp Drift Boundaries...")

    secret = "fsp_webhook_secret_key_prod_99812736"
    t_header = 1775419200
    payload = json.dumps({"event": "invitation.accepted", "invitation_id": 551})
    sig_header = generate_fsp_signature(payload, secret, t_header)

    # Boundary tests against current_time
    # Exact match: drift = 0
    ok, reason = verify_fsp_signature(payload, sig_header, secret, current_time=t_header)
    assert ok is True, f"drift=0 rejected: {reason}"

    # Inside window (past): drift = +299s
    ok, reason = verify_fsp_signature(payload, sig_header, secret, current_time=t_header + 299)
    assert ok is True, f"drift=+299s rejected: {reason}"

    # Exact boundary (past): drift = +300s
    ok, reason = verify_fsp_signature(payload, sig_header, secret, current_time=t_header + 300)
    assert ok is True, f"drift=+300s rejected: {reason}"

    # Exceeded boundary (past): drift = +301s -> MUST REJECT (HTTP 401 Replay Attack)
    ok, reason = verify_fsp_signature(payload, sig_header, secret, current_time=t_header + 301)
    assert ok is False, "drift=+301s was accepted!"
    assert "ERR_TIMESTAMP_DRIFT_EXCEEDED" in reason

    # Extreme past: drift = +10,000s
    ok, reason = verify_fsp_signature(payload, sig_header, secret, current_time=t_header + 10000)
    assert ok is False, "drift=+10000s was accepted!"

    # Inside window (future clock skew): drift = -299s
    ok, reason = verify_fsp_signature(payload, sig_header, secret, current_time=t_header - 299)
    assert ok is True, f"drift=-299s rejected: {reason}"

    # Exact boundary (future clock skew): drift = -300s
    ok, reason = verify_fsp_signature(payload, sig_header, secret, current_time=t_header - 300)
    assert ok is True, f"drift=-300s rejected: {reason}"

    # Exceeded boundary (future clock skew): drift = -301s -> MUST REJECT
    ok, reason = verify_fsp_signature(payload, sig_header, secret, current_time=t_header - 301)
    assert ok is False, "drift=-301s was accepted!"
    assert "ERR_TIMESTAMP_DRIFT_EXCEEDED" in reason

    # Extreme future: drift = -50,000s
    ok, reason = verify_fsp_signature(payload, sig_header, secret, current_time=t_header - 50000)
    assert ok is False, "drift=-50000s was accepted!"

    print("[PASS] Test 2: Timestamp drift boundaries (-300s <= drift <= +300s) verified.")


def test_replay_idempotency_cache():
    """Simulates adversarial replay attempts with identical delivery IDs."""
    print(">>> [TEST 3] Replay Attack Simulation with Idempotency Cache...")

    cache = WebhookDeliveryReplayCache(ttl_seconds=300)
    secret = "fsp_test_secret_for_cache_991823"
    t_send = 1775419200
    delivery_id = "deliv-uuid-7b2a9c1d-4567-4890"
    payload = json.dumps({"event": "invitation.accepted", "candidate_id": 1042})
    sig_header = generate_fsp_signature(payload, secret, t_send)

    # 1. Initial valid transmission at t = t_send + 10s
    status_code, msg = cache.process_delivery(delivery_id, payload, sig_header, secret, current_time=t_send + 10)
    assert status_code == 200, f"Initial delivery failed: {msg}"
    assert msg == "DELIVERED"

    # 2. Adversarial replay within 300s window at t = t_send + 45s (same signature, same delivery_id)
    status_code, msg = cache.process_delivery(delivery_id, payload, sig_header, secret, current_time=t_send + 45)
    assert status_code == 409, f"Replay should be rejected with HTTP 409 Conflict, got {status_code}"
    assert msg == "ERR_DUPLICATE_DELIVERY_REPLAY_DETECTED"

    # 3. Third replay attempt at t = t_send + 290s
    status_code, msg = cache.process_delivery(delivery_id, payload, sig_header, secret, current_time=t_send + 290)
    assert status_code == 409, "Replay should be rejected by deduplication cache"

    # 4. Replay attempt after window expiration at t = t_send + 305s
    status_code, msg = cache.process_delivery(delivery_id, payload, sig_header, secret, current_time=t_send + 305)
    assert status_code == 401, f"Expired replay should be rejected with HTTP 401 Unauthorized, got {status_code}"
    assert "ERR_TIMESTAMP_DRIFT_EXCEEDED" in msg

    print("[PASS] Test 3: Idempotency deduplication & expired replay rejection verified.")


def test_exponential_retry_schedule_and_dlq_lifecycle():
    """Simulates exponential retry schedule (1m, 5m, 15m, 1h, 24h) and DLQ transition."""
    print(">>> [TEST 4] Exponential Retry Schedule & DLQ Lifecycle Simulation...")

    dispatcher = WebhookDeliveryDispatcher()

    # Verify schedule constants
    expected_intervals = [60, 300, 900, 3600, 86400]
    assert dispatcher.intervals == expected_intervals, f"Intervals mismatch: {dispatcher.intervals}"

    # Verify cumulative duration
    total_retry_seconds = sum(expected_intervals)
    assert total_retry_seconds == 91260, f"Cumulative retry delay: {total_retry_seconds}s (expected 91260s / 25h 21m)"

    # Simulation Scenario A: Transient 500 errors leading to DLQ
    consecutive_failures = 0

    # Attempt 0: t = 0 (Initial attempt fails with HTTP 500)
    step1 = dispatcher.evaluate_delivery_attempt(consecutive_failures=0, http_status=500)
    assert step1["status"] == "retry_pending"
    assert step1["attempt"] == 1
    assert step1["delay_seconds"] == 60  # 1m

    # Attempt 1 fails (HTTP 502 Bad Gateway)
    step2 = dispatcher.evaluate_delivery_attempt(consecutive_failures=1, http_status=502)
    assert step2["status"] == "retry_pending"
    assert step2["attempt"] == 2
    assert step2["delay_seconds"] == 300  # 5m

    # Attempt 2 fails (HTTP 503 Service Unavailable)
    step3 = dispatcher.evaluate_delivery_attempt(consecutive_failures=2, http_status=503)
    assert step3["status"] == "retry_pending"
    assert step3["attempt"] == 3
    assert step3["delay_seconds"] == 900  # 15m

    # Attempt 3 fails (HTTP 504 Gateway Timeout)
    step4 = dispatcher.evaluate_delivery_attempt(consecutive_failures=3, http_status=504)
    assert step4["status"] == "retry_pending"
    assert step4["attempt"] == 4
    assert step4["delay_seconds"] == 3600  # 1h

    # Attempt 4 fails (Network Connection Timeout)
    step5 = dispatcher.evaluate_delivery_attempt(consecutive_failures=4, http_status=None, network_error="ConnectionRefusedError")
    assert step5["status"] == "retry_pending"
    assert step5["attempt"] == 5
    assert step5["delay_seconds"] == 86400  # 24h

    # Attempt 5 fails (HTTP 500 Internal Error) -> Exhausted all 5 retries!
    step6 = dispatcher.evaluate_delivery_attempt(consecutive_failures=5, http_status=500)
    assert step6["status"] == "dead_letter", f"Expected 'dead_letter', got {step6['status']}"
    assert step6["attempt"] == 5
    assert step6["delay_seconds"] is None
    assert step6["retryable"] is False

    # Simulation Scenario B: Fatal 4xx Client Error (Non-retryable)
    # Employer endpoint returns HTTP 404 (wrong URL) or 401 (invalid secret)
    for client_err in [400, 401, 403, 404, 422]:
        fatal_step = dispatcher.evaluate_delivery_attempt(consecutive_failures=0, http_status=client_err)
        assert fatal_step["status"] == "rejected_by_receiver", f"Status for {client_err} should be rejected_by_receiver"
        assert fatal_step["delay_seconds"] is None
        assert fatal_step["retryable"] is False

    # Simulation Scenario C: Transient failure recovered on Attempt 2
    rec_step0 = dispatcher.evaluate_delivery_attempt(consecutive_failures=0, http_status=500)
    assert rec_step0["status"] == "retry_pending"
    rec_step1 = dispatcher.evaluate_delivery_attempt(consecutive_failures=1, http_status=200)
    assert rec_step1["status"] == "delivered"
    assert rec_step1["delay_seconds"] is None
    assert rec_step1["retryable"] is False

    # Simulation Scenario D: Manual DLQ requeue via POST /retry
    # When a message in DLQ is manually retried, it enters a new cycle
    requeued_step = dispatcher.evaluate_delivery_attempt(consecutive_failures=0, http_status=500)
    assert requeued_step["status"] == "retry_pending"
    assert requeued_step["delay_seconds"] == 60

    print("[PASS] Test 4: Retry intervals [60, 300, 900, 3600, 86400] and DLQ lifecycle verified.")


def test_schema_and_db_consistency_audit():
    """
    Performs adversarial consistency audit between doc specifications:
    1. AtsProviderEnum vs DB chk_ats_type
    2. WebhookDeliveryLogItem status literals
    3. UpdateAtsConfigRequest webhook_secret length
    """
    print(">>> [TEST 5] OpenAPI Contracts & Domain Model Cross-Specification Audit...")

    doc4_path = Path("docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md")
    doc2_path = Path("docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md")

    assert doc4_path.exists(), "docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md not found"
    assert doc2_path.exists(), "docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md not found"

    doc4_text = doc4_path.read_text(encoding="utf-8")
    doc2_text = doc2_path.read_text(encoding="utf-8")

    # 1. Audit ATS provider types
    # In doc 04: AtsProviderEnum has "generic_webhook"
    # In doc 02: chk_ats_type has 'custom_webhook'
    has_generic_webhook = "GENERIC_WEBHOOK = \"generic_webhook\"" in doc4_text
    has_custom_webhook = "'custom_webhook'" in doc2_text

    print(f"    - Doc 04 contains GENERIC_WEBHOOK: {has_generic_webhook}")
    print(f"    - Doc 02 contains 'custom_webhook': {has_custom_webhook}")

    if has_generic_webhook and has_custom_webhook:
        print("    [FINDING 1] Potential naming divergence: OpenAPI uses 'generic_webhook' while DB CHECK uses 'custom_webhook'.")

    # 2. Audit WebhookDeliveryLogItem status Literal
    has_rejected_by_receiver_in_literal = 'Literal["delivered", "retry_pending", "dead_letter", "rejected_by_receiver"]' in doc4_text
    print(f"    - WebhookDeliveryLogItem includes 'rejected_by_receiver' in Literal: {has_rejected_by_receiver_in_literal}")
    if not has_rejected_by_receiver_in_literal:
        print("    [FINDING 2] WebhookDeliveryLogItem status is Literal['delivered', 'retry_pending', 'dead_letter']. Section 5.4 specifies 'rejected_by_receiver' for fatal 4xx errors.")

    # 3. Audit secret length constraints
    assert "min_length=16, max_length=128" in doc4_text, "webhook_secret constraint min_length=16 missing from doc 04"
    print("    - UpdateAtsConfigRequest: webhook_secret min_length=16, max_length=128 confirmed.")

    # 4. Audit salary constraint in ATS vacancy import
    assert "gt=0, description=\"Минимальная зарплата в рублях (> 0)\"" in doc4_text
    assert "salary_currency: Literal[\"RUB\"] = \"RUB\"" in doc4_text
    assert "if ratio > 3.5:" in doc4_text
    print("    - AtsVacancyImportRequest: salary_min > 0, currency RUB, ratio <= 3.5 confirmed.")

    print("[PASS] Test 5: Contract & Domain Model cross-specification audit complete.")


def test_section6_quality_gate_execution():
    """Extracts and executes Section 6 Quality Gate script from doc 04."""
    print(">>> [TEST 6] Executing Section 6 Embedded Quality Gate Script...")

    doc4_path = Path("docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md")
    doc_text = doc4_path.read_text(encoding="utf-8")

    assert "```python\n#!/usr/bin/env python3" in doc_text, "Quality gate code block marker not found"
    script_block = doc_text.split("```python\n#!/usr/bin/env python3")[1].split("```")[0]
    
    # Execute script block in isolated environment
    scope: Dict[str, Any] = {}
    exec(script_block, scope)

    assert "run_milestone4_quality_gate" in scope, "run_milestone4_quality_gate function not defined"
    exit_code = scope["run_milestone4_quality_gate"]()
    assert exit_code == 0, f"Quality gate returned non-zero exit code: {exit_code}"

    print("[PASS] Test 6: Embedded Section 6 Quality Gate passed with exit code 0.")


def test_section6_reference_function_micro_audit():
    """
    Directly exercises Section 6's raw `verify_webhook_signature` implementation
    against adversarial corner cases to document exact behavior and caveats.
    """
    print(">>> [TEST 7] Section 6 Reference Implementation Micro-Audit...")

    doc4_path = Path("docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md")
    doc_text = doc4_path.read_text(encoding="utf-8")
    script_block = doc_text.split("```python\n#!/usr/bin/env python3")[1].split("```")[0]
    scope: Dict[str, Any] = {}
    exec(script_block, scope)

    verify_fn = scope["verify_webhook_signature"]
    generate_fn = scope["generate_webhook_signature"]

    secret = "secret_key_12345678"
    t = 1775419200
    payload = json.dumps({"test": 1})
    valid_sig = generate_fn(payload, secret, t)

    # 1. Exact canonical matches
    assert verify_fn(payload, valid_sig, secret, t) is True
    assert verify_fn(payload, valid_sig, secret, t + 300) is True  # Exactly +300s
    assert verify_fn(payload, valid_sig, secret, t + 301) is False # +301s rejected
    assert verify_fn(payload, valid_sig, secret, t - 300) is True  # Exactly -300s
    assert verify_fn(payload, valid_sig, secret, t - 301) is False # -301s rejected

    # 2. Spaces after comma in header
    # 't=1775419200, v1=...'
    spaced_sig = valid_sig.replace(",", ", ")
    spaced_result = verify_fn(payload, spaced_sig, secret, t)
    # Section 6 implementation does not strip keys, so ' v1' != 'v1' -> returns False
    assert spaced_result is False, "Section 6 reference parser rejects space-separated header parameters"
    print("    [NOTE] Section 6 reference verify_webhook_signature requires no spaces around commas (e.g. 't=...,v1=...').")

    # 3. Uppercase hex signature
    # Section 6 compares v1 directly with hexdigest() (lowercase), so uppercase v1 fails
    parts = valid_sig.split(",")
    upper_sig = f"{parts[0]},{parts[1].upper()}"
    upper_result = verify_fn(payload, upper_sig, secret, t)
    assert upper_result is False, "Section 6 reference parser is strictly lowercase-hex sensitive"
    print("    [NOTE] Section 6 reference verify_webhook_signature expects strictly lowercase hex digest in v1.")

    # 4. Inverted parameters: 'v1=...,t=...'
    inverted_sig = f"{parts[1]},{parts[0]}"
    assert verify_fn(payload, inverted_sig, secret, t) is True, "Inverted parameters should succeed"

    # 5. Non-integer timestamp: 't=1775419200.5,v1=...'
    float_sig = f"t={t}.5,{parts[1]}"
    assert verify_fn(payload, float_sig, secret, t) is False, "Float timestamp safely rejected"

    print("[PASS] Test 7: Section 6 reference implementation micro-audit complete.")


# ==============================================================================
# MAIN TEST HARNESS
# ==============================================================================

def main():
    print("=" * 80)
    print("CHALLENGER M4-2 ADVERSARIAL STRESS TEST SUITE")
    print("Milestone 4: ATS Webhooks, Replay Tolerance, Exponential Retries, DLQ")
    print("=" * 80)

    test_hmac_signature_correctness_and_variations()
    test_replay_attack_tolerance_boundaries()
    test_replay_idempotency_cache()
    test_exponential_retry_schedule_and_dlq_lifecycle()
    test_schema_and_db_consistency_audit()
    test_section6_quality_gate_execution()
    test_section6_reference_function_micro_audit()

    print("=" * 80)
    print("### ALL CHALLENGER M4-2 STRESS TESTS PASSED (EXIT CODE 0) ###")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())

