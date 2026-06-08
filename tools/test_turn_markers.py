#!/usr/bin/env python3
"""
Conformance tests for PAIRL v1.3 in-body turn markers (rule V11).

Runnable, dependency-free:

    python tools/test_turn_markers.py

Exits 0 if all cases pass, 1 otherwise. Each case wraps a body in a minimal
valid header block and asserts the reference validator's verdict (and, for the
negative cases, that the expected V11 error is reported).
"""

import sys

from validator import PAIRLMessage

HEADER = (
    "@v 1\n"
    "@mid ref:msg:01JH0Q8A1B2C3D4E5F6G7H8I9J\n"
    "@ts 2026-06-08T10:15:00.000+02:00\n\n"
)


def check(name: str, body: str, should_pass: bool, expect_substr: str = "") -> bool:
    msg = PAIRLMessage(HEADER + body)
    ok = msg.validate()
    passed = ok == should_pass
    if passed and not should_pass and expect_substr:
        passed = any(expect_substr in e for e in msg.errors)
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}")
    if not passed:
        print(f"         expected valid={should_pass}, got valid={ok}; errors={msg.errors}")
    return passed


CASES = [
    # --- valid ---
    ("compact markers, section grouping", (
        "#u1\n"
        "req{t=db_migration,s=f,l=2} @rid=a1\n"
        "#fact current_version=pg12 @rid=f1\n"
        "#a2\n"
        "pln{t=strategy,s=f,l=2} @rid=a2\n"
        "#fact tool=aws_dms @rid=f2\n"
    ), True, ""),
    ("verbose #msg long form", (
        "#msg m1 r=u parent=-\n"
        "req{t=x,s=f,l=1} @rid=a1\n"
        "#msg m2 r=a parent=m1\n"
        "ack{t=x,s=f,l=1} @rid=a2\n"
    ), True, ""),
    ("@m= override to a declared marker", (
        "#u1\n"
        "req{t=x,s=f,l=1} @rid=a1\n"
        "#a2\n"
        "ack{t=x,s=f,l=1} @rid=a2\n"
        "#fact noted_earlier=true @m=u1 @rid=f1\n"
    ), True, ""),
    ("legacy v1.2 body, no markers", (
        "req{t=x,s=f,l=1} @rid=a1\n"
        "#fact k=v @rid=f1\n"
    ), True, ""),
    # --- invalid ---
    ("duplicate compact marker", (
        "#u1\n"
        "req{t=x} @rid=a1\n"
        "#u1\n"
        "qst{t=y} @rid=a2\n"
    ), False, "duplicate turn marker"),
    ("dangling @m= reference", (
        "#u1\n"
        "req{t=x} @rid=a1\n"
        "#fact k=v @m=a9 @rid=f1\n"
    ), False, "references undeclared turn marker"),
    ("malformed #msg (missing parent)", (
        "#msg m1 r=u\n"
        "req{t=x} @rid=a1\n"
    ), False, "malformed #msg"),
    ("verbose parent references undeclared id", (
        "#msg m1 r=u parent=m9\n"
        "req{t=x} @rid=a1\n"
    ), False, "references undeclared turn marker"),
]


def main() -> None:
    print("PAIRL v1.3 turn-marker conformance (V11)")
    print("-" * 50)
    results = [check(*c) for c in CASES]
    print("-" * 50)
    passed, total = sum(results), len(results)
    print(f"{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
