#!/usr/bin/env python
"""
FKT Test Runner
===============
Single command to run all tests with a clear pass/fail summary and coverage.

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py --fast       # Skip slow/integration tests
    python run_tests.py --verbose    # Show individual test names

Exit code: 0 if all pass, 1 if any fail.
"""

import subprocess
import sys
import os
import time

# ── Test suites to run, in priority order ──────────────────────────────────
TEST_SUITES = [
    {
        "name": "SM-2 Algorithm",
        "module": "tracker_app.tests.test_sm2",
        "description": "Core memory scheduling math",
        "critical": True,
    },
    {
        "name": "LearningTracker CRUD",
        "module": "tracker_app.tests.test_learning_tracker",
        "description": "Database operations and review logic",
        "critical": True,
    },
    {
        "name": "API Endpoints",
        "module": "tracker_app.tests.test_api",
        "description": "Flask REST API behavior",
        "critical": True,
    },
    {
        "name": "Privacy Filter",
        "module": "tracker_app.tests.test_privacy_filter",
        "description": "PII detection and redaction",
        "critical": False,
    },
    {
        "name": "Text Quality Validator",
        "module": "tracker_app.tests.test_text_quality",
        "description": "Garbage text filtering",
        "critical": False,
    },
    {
        "name": "Config Validation",
        "module": "tracker_app.tests.test_config",
        "description": "Configuration sanity checks",
        "critical": False,
    },
]


def run_suite(suite: dict, verbose: bool = False) -> dict:
    """Run a single test suite and return results."""
    args = [sys.executable, "-m", "pytest", "-x"]
    if verbose:
        args.append("-v")
    else:
        args.append("-q")
    args.append(f"tracker_app/tests/{suite['module'].split('.')[-1]}.py")

    start = time.time()
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    elapsed = time.time() - start

    return {
        "name": suite["name"],
        "description": suite["description"],
        "passed": result.returncode == 0,
        "critical": suite["critical"],
        "elapsed": elapsed,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def print_header():
    print("\n" + "=" * 60)
    print("  FKT AUTOMATED TEST SUITE")
    print("=" * 60)


def print_suite_result(result: dict):
    icon = "✅" if result["passed"] else ("🔴" if result["critical"] else "🟡")
    status = "PASS" if result["passed"] else "FAIL"
    elapsed = f"{result['elapsed']:.1f}s"
    print(f"  {icon} [{status}] {result['name']:<30} {elapsed:>6}  — {result['description']}")


def print_failures(results: list):
    failed = [r for r in results if not r["passed"]]
    if not failed:
        return
    print("\n" + "─" * 60)
    print("  FAILURE DETAILS")
    print("─" * 60)
    for r in failed:
        print(f"\n❌ {r['name']}:\n")
        # Show the last 30 lines of output (most relevant)
        output = (r["stdout"] + r["stderr"]).strip()
        lines = output.split("\n")
        for line in lines[-30:]:
            print(f"    {line}")


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    fast = "--fast" in sys.argv

    print_header()
    print(f"\n  Root: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"  Python: {sys.executable}\n")
    print("─" * 60)

    results = []
    critical_failed = False

    for suite in TEST_SUITES:
        if fast and not suite["critical"]:
            print(f"  ⏭️  [SKIP]  {suite['name']:<30}        — skipped (--fast)")
            continue

        result = run_suite(suite, verbose=verbose)
        results.append(result)
        print_suite_result(result)

        if not result["passed"] and result["critical"]:
            critical_failed = True

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    total_time = sum(r["elapsed"] for r in results)

    print(f"  RESULTS: {passed}/{total} passed  |  {failed} failed  |  {total_time:.1f}s total")

    if failed == 0:
        print("\n  🎉 ALL TESTS PASSED — Backend is verified!")
    elif critical_failed:
        print("\n  🔴 CRITICAL TESTS FAILED — App will crash in production!")
    else:
        print("\n  🟡 Some non-critical tests failed — Review before shipping.")

    print("=" * 60 + "\n")

    print_failures(results)

    # Exit 0 = all pass, 1 = any fail
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
