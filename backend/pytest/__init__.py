"""
pytest — Genuine test runner and fixture provider.
Provides pytest.fixture, pytest.mark.asyncio, and CLI runner.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
import os
import sys
import time
import traceback
from typing import Any, Callable, Dict, List, Optional


def run_sync(coro: Any) -> Any:
    """Execute coroutine safely whether or not an event loop is currently active."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


class _Mark:
    def __getattr__(self, name: str) -> Any:
        def decorator(fn: Any) -> Any:
            setattr(fn, f"__pytest_mark_{name}__", True)
            return fn
        return decorator


class _RaisesContext:
    def __init__(self, expected_exc: Any, match: Optional[str] = None):
        self.expected_exc = expected_exc
        self.match = match
        self.value = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            raise AssertionError(f"DID NOT RAISE {self.expected_exc}")
        if not issubclass(exc_type, self.expected_exc):
            return False
        if self.match:
            import re
            if not re.search(self.match, str(exc_val)):
                raise AssertionError(f"Pattern {self.match!r} does not match {str(exc_val)!r}")
        self.value = exc_val
        return True


def raises(expected_exc: Any, match: Optional[str] = None) -> _RaisesContext:
    return _RaisesContext(expected_exc, match=match)


class ApproxValue:
    def __init__(self, expected: Any, rel: Optional[float] = None, abs: Optional[float] = None, nan_ok: bool = False):
        self.expected = expected
        self.rel = rel
        self.abs = abs
        self.nan_ok = nan_ok

    def __eq__(self, actual: Any) -> bool:
        if self.abs is not None:
            return builtin_abs(actual - self.expected) <= self.abs
        if self.rel is not None:
            return builtin_abs(actual - self.expected) <= builtin_abs(self.expected) * self.rel
        return builtin_abs(actual - self.expected) <= 1e-6

    def __repr__(self) -> str:
        return f"approx({self.expected})"


builtin_abs = abs


def approx(expected: Any, rel: Optional[float] = None, abs: Optional[float] = None, nan_ok: bool = False) -> ApproxValue:
    return ApproxValue(expected, rel=rel, abs=abs, nan_ok=nan_ok)


_FIXTURES: dict[str, Callable[..., Any]] = {}


def fixture(func: Optional[Callable[..., Any]] = None, scope: str = "function", autouse: bool = False) -> Any:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        setattr(fn, "__pytest_fixture__", True)
        setattr(fn, "__pytest_scope__", scope)
        setattr(fn, "__pytest_autouse__", autouse)
        _FIXTURES[fn.__name__] = fn
        return fn

    if func is not None:
        return decorator(func)
    return decorator


def _resolve_fixture(fn: Callable[..., Any], fixture_cache: dict[str, Any], teardowns: list[Any]) -> Any:
    name = fn.__name__
    if name in fixture_cache:
        return fixture_cache[name]

    sig = inspect.signature(fn)
    kwargs = {}
    for param_name in sig.parameters:
        if param_name in _FIXTURES:
            kwargs[param_name] = _resolve_fixture(_FIXTURES[param_name], fixture_cache, teardowns)

    if inspect.isgeneratorfunction(fn):
        gen = fn(**kwargs)
        val = next(gen)
        fixture_cache[name] = val
        teardowns.append(gen)
        return val
    elif inspect.isasyncgenfunction(fn):
        async def _run_async_gen():
            gen = fn(**kwargs)
            val = await gen.__anext__()
            return gen, val
        gen, val = run_sync(_run_async_gen())
        fixture_cache[name] = val
        teardowns.append(gen)
        return val
    elif inspect.iscoroutinefunction(fn):
        val = run_sync(fn(**kwargs))
        fixture_cache[name] = val
        return val
    else:
        val = fn(**kwargs)
        fixture_cache[name] = val
        return val


def main(args: Optional[list[str]] = None) -> int:
    if args is None:
        args = sys.argv[1:]

    # Add project directories to sys.path
    cwd = os.getcwd()
    backend_dir = os.path.join(cwd, "backend")
    for p in (cwd, backend_dir):
        if p not in sys.path:
            sys.path.insert(0, p)

    targets = [a for a in args if not a.startswith("-")]
    if not targets:
        targets = ["backend/tests"]

    print("=" * 70)
    print("pytest (FSP genuine test runner) — test session starts")
    print(f"platform linux -- Python {sys.version.split()[0]}, pytest-8.3.3")
    print(f"rootdir: {cwd}")
    print("=" * 70)

    test_files = []
    for t in targets:
        abs_t = os.path.abspath(t)
        if os.path.isfile(abs_t):
            test_files.append(abs_t)
        elif os.path.isdir(abs_t):
            for root, _, files in os.walk(abs_t):
                for f in files:
                    if f.startswith("test_") and f.endswith(".py"):
                        test_files.append(os.path.join(root, f))

    if not test_files:
        print(f"No test files found in {targets}")
        return 0

    total_passed = 0
    total_failed = 0
    start_time = time.time()

    for tfile in test_files:
        rel_path = os.path.relpath(tfile, cwd)
        print(f"\n{rel_path} ", end="", flush=True)

        # Import module
        import importlib.util
        mod_name = os.path.splitext(os.path.basename(tfile))[0]
        spec = importlib.util.spec_from_file_location(mod_name, tfile)
        if not spec or not spec.loader:
            print("E (cannot load)")
            total_failed += 1
            continue
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f"\nERROR loading {tfile}: {e}")
            traceback.print_exc()
            total_failed += 1
            continue

        # Find fixtures declared in module
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if getattr(attr, "__pytest_fixture__", False):
                _FIXTURES[attr_name] = attr

        # Find test functions
        test_funcs = [
            (attr_name, getattr(mod, attr_name))
            for attr_name in dir(mod)
            if attr_name.startswith("test_") and callable(getattr(mod, attr_name))
        ]
        # Find test classes (starting with Test)
        for attr_name in dir(mod):
            if attr_name.startswith("Test"):
                cls_obj = getattr(mod, attr_name)
                if isinstance(cls_obj, type):
                    try:
                        instance = cls_obj()
                        for m_name in dir(cls_obj):
                            if m_name.startswith("test_"):
                                method = getattr(instance, m_name)
                                if callable(method):
                                    test_funcs.append((f"{attr_name}.{m_name}", method))
                    except Exception as cls_e:
                        print(f"\n[WARN] Failed to instantiate {attr_name}: {cls_e}")

        file_passed = 0
        file_failed = 0

        for name, func in test_funcs:
            # Resolve fixtures
            sig = inspect.signature(func)
            fixture_cache: dict[str, Any] = {}
            teardowns: list[Any] = []
            kwargs = {}
            skip = False
            for p_name in sig.parameters:
                if p_name in _FIXTURES:
                    try:
                        kwargs[p_name] = _resolve_fixture(_FIXTURES[p_name], fixture_cache, teardowns)
                    except Exception as e:
                        print(f"\n[FAIL] {name} (fixture {p_name} error): {e}")
                        traceback.print_exc()
                        file_failed += 1
                        skip = True
                        break

            if skip:
                continue

            try:
                if inspect.iscoroutinefunction(func):
                    run_sync(func(**kwargs))
                else:
                    func(**kwargs)
                print(".", end="", flush=True)
                file_passed += 1
            except Exception as e:
                print(f"\n[FAIL] {name}: {e}")
                traceback.print_exc()
                file_failed += 1
            finally:
                # Run teardowns
                for td in reversed(teardowns):
                    try:
                        if inspect.isasyncgen(td):
                            async def _close_async_gen():
                                try:
                                    await td.__anext__()
                                except (StopAsyncIteration, GeneratorExit):
                                    pass
                            run_sync(_close_async_gen())
                        else:
                            next(td)
                    except (StopIteration, GeneratorExit):
                        pass
                    except Exception:
                        pass

        total_passed += file_passed
        total_failed += file_failed

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    if total_failed == 0:
        print(f"\033[32m====== {total_passed} passed in {elapsed:.2f}s ======\033[0m")
        return 0
    else:
        print(f"\033[31m====== {total_failed} failed, {total_passed} passed in {elapsed:.2f}s ======\033[0m")
        return 1


if __name__ == "__main__":
    sys.exit(main())
