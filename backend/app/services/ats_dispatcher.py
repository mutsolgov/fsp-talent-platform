"""
FSP IT-Talent Platform — ATS Webhook Dispatcher & Export Gateway.
Signs payloads with HMAC-SHA256 (X-FSP-Signature), enforces 300s replay window,
implements exponential backoff (1m, 5m, 15m) and DLQ logging.
Defined in docs/02 §5.5, docs/04 §5, and DISPATCH.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional, Tuple

REPLAY_WINDOW_SECONDS = 300
RETRY_DELAYS_SECONDS = [60, 300, 900]  # 1m, 5m, 15m
FAST_RETRY_DELAYS_SECONDS = [1, 2, 4, 8, 16]  # Fast retry schedule (1s, 2s, 4s, 8s, 16s)


def sign_payload(secret: str, payload_bytes: bytes) -> str:
    """Computes HMAC-SHA256 signature for webhook payload."""
    secret_bytes = secret.encode("utf-8")
    mac = hmac.new(secret_bytes, payload_bytes, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def verify_signature(secret: str, payload_bytes: bytes, signature_header: str) -> bool:
    """Validates X-FSP-Signature header against secret and payload."""
    if not secret or not signature_header:
        return False

    expected = sign_payload(secret, payload_bytes)
    # Support both 'sha256=HEX' and raw 'HEX'
    if signature_header.startswith("sha256="):
        return hmac.compare_digest(expected, signature_header)
    expected_hex = expected.split("=")[-1]
    return hmac.compare_digest(expected_hex, signature_header)


def verify_timestamp(timestamp_sec: int, max_drift_seconds: int = REPLAY_WINDOW_SECONDS) -> bool:
    """Verifies that the request timestamp is within the anti-replay window (300s)."""
    now = int(time.time())
    return abs(now - timestamp_sec) <= max_drift_seconds


class AtsDispatcher:
    """
    Manages webhook dispatches, retry policies, and dead-letter queue (DLQ) logging.
    """

    def __init__(self, retry_delays: Optional[List[int]] = None):
        self.retry_delays: List[int] = list(retry_delays) if retry_delays is not None else list(RETRY_DELAYS_SECONDS)
        self.dlq_log: List[Dict[str, Any]] = []

    def build_headers(self, secret: str, payload_bytes: bytes, event_type: str = "invitation.accepted") -> Dict[str, str]:
        """Constructs security and routing headers for ATS webhook dispatch."""
        now_ts = int(time.time())
        signature = sign_payload(secret, payload_bytes)
        return {
            "Content-Type": "application/json",
            "X-FSP-Signature": signature,
            "X-FSP-Timestamp": str(now_ts),
            "X-FSP-Event": event_type,
            "User-Agent": "FSP-Platform-ATS-Dispatcher/1.0",
        }

    def format_huntflow_candidate(self, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Formats candidate dossier for Huntflow ATS API."""
        return {
            "first_name": candidate_data.get("first_name", ""),
            "last_name": candidate_data.get("last_name", ""),
            "middle_name": candidate_data.get("middle_name"),
            "email": candidate_data.get("email"),
            "phone": candidate_data.get("phone"),
            "telegram": candidate_data.get("telegram"),
            "position": f"{candidate_data.get('specialization', 'Backend')} {candidate_data.get('grade', 'Middle')}",
            "money": candidate_data.get("expected_salary"),
            "skills": [{"name": s} for s in candidate_data.get("skills", [])],
            "fsp_verification": {
                "fsp_id": candidate_data.get("fsp_id"),
                "fsp_verified": candidate_data.get("fsp_verified", False),
                "test_score": candidate_data.get("test_score", 0.0),
            },
        }

    def format_hh_candidate(self, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Formats candidate dossier for HeadHunter (HH) ATS API."""
        return {
            "last_name": candidate_data.get("last_name", ""),
            "first_name": candidate_data.get("first_name", ""),
            "middle_name": candidate_data.get("middle_name"),
            "contact": [
                {"type": {"id": "cell"}, "value": candidate_data.get("phone")} if candidate_data.get("phone") else None,
                {"type": {"id": "email"}, "value": candidate_data.get("email")} if candidate_data.get("email") else None,
            ],
            "title": f"{candidate_data.get('specialization', 'Backend')} {candidate_data.get('grade', 'Middle')}",
            "salary": {"amount": candidate_data.get("expected_salary"), "currency": "RUR"},
            "skill_set": candidate_data.get("skills", []),
        }

    def handle_dispatch_failure(
        self,
        event_id: str,
        webhook_url: str,
        payload: Dict[str, Any],
        attempt_number: int,
        error_message: str,
    ) -> Dict[str, Any]:
        """
        Calculates next retry delay or routes to Dead Letter Queue (DLQ) if attempts exhausted.
        """
        if attempt_number < len(self.retry_delays):
            next_delay = self.retry_delays[attempt_number]
            return {
                "status": "retry_scheduled",
                "attempt": attempt_number + 1,
                "next_retry_delay_seconds": next_delay,
                "is_dlq": False,
            }
        else:
            dlq_entry = {
                "event_id": event_id,
                "webhook_url": webhook_url,
                "payload": payload,
                "attempts_exhausted": attempt_number + 1,
                "last_error": error_message,
                "moved_to_dlq_at": datetime.now(timezone.utc).isoformat(),
            }
            self.dlq_log.append(dlq_entry)
            return {
                "status": "dlq_routed",
                "attempt": attempt_number + 1,
                "next_retry_delay_seconds": None,
                "is_dlq": True,
                "dlq_entry": dlq_entry,
            }
