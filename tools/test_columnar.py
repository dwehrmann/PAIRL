#!/usr/bin/env python3
"""
Conformance tests for PAIRL v1.5 columnar record blocks (rule V12).

Runnable, dependency-free:

    python tools/test_columnar.py

Exits 0 if all cases pass, 1 otherwise. Each case wraps a body in a minimal
valid header block and asserts the reference validator's verdict (and, for the
negative cases, the expected error substring). A second group asserts that
columnar rows expand to the equivalent `#type key=value` records (§9.4a).
"""

import sys

from validator import PAIRLMessage

HEADER = (
    "@v 1\n"
    "@id m1\n"
    "@ts 2026-06-22T10:15:00.000+02:00\n\n"
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
    ("evid columnar block, 3 cols", (
        "#evid[claim,src,conf]\n"
        '"LLM costs decreased 60% in 2025" s1 0.85\n'
        '"Multi-agent adoption increased 300%" s2 0.90\n'
    ), True, ""),
    ("quota columnar block, 4 cols", (
        "#quota[type,total,used,rem]\n"
        "tokens 50000 38500 11500\n"
        "api_calls 25 18 7\n"
    ), True, ""),
    ("quoted field with comma and = sign", (
        "#evid[claim,src,conf]\n"
        '"cost = 60% lower, broadly" s1 0.80\n'
    ), True, ""),
    ("block closes at next #-record", (
        "#evid[claim,src,conf]\n"
        '"x happened" s1 0.50\n'
        "#fact note=after_block\n"
    ), True, ""),
    ("per-row @rid tag", (
        "#evid[claim,src,conf]\n"
        '"x happened" s1 0.50 @rid=e1\n'
    ), True, ""),
    ("columnar block mixed with key=value evid", (
        "#evid[claim,src,conf]\n"
        '"x happened" s1 0.50\n'
        '#evid claim="y happened" src=s2 conf=0.6\n'
    ), True, ""),
    # --- invalid ---
    ("row has too few fields", (
        "#evid[claim,src,conf]\n"
        '"only two" s1\n'
    ), False, "expected 3"),
    ("row has too many fields (unquoted spaces)", (
        "#evid[claim,src,conf]\n"
        "unquoted claim with spaces s1 0.85\n"
    ), False, "expected 3"),
    ("duplicate column key", (
        "#evid[claim,claim,conf]\n"
        '"x" "y" 0.5\n'
    ), False, "duplicate column key"),
    ("columnar not allowed for #fact (key is data)", (
        "#fact[key,val]\n"
        "deadline 2026-02-05\n"
    ), False, "not allowed for #fact"),
    ("columnar not allowed for #ref (key is data)", (
        "#ref[name,val]\n"
        "src ref:url:x:2026-01-01\n"
    ), False, "not allowed for #ref"),
    ("expanded evid still needs conf (V2)", (
        "#evid[claim,src]\n"
        '"x happened" s1\n'
    ), False, "missing required fields"),
]


def check_expansion(name: str, body: str, expected_records: list) -> bool:
    msg = PAIRLMessage(HEADER + body)
    got = [r for r in msg.records if r.startswith("#evid") or r.startswith("#quota")]
    passed = got == expected_records
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}")
    if not passed:
        print(f"         expected {expected_records}")
        print(f"         got      {got}")
    return passed


EXPANSION_CASES = [
    ("evid rows expand to key=value", (
        "#evid[claim,src,conf]\n"
        '"LLM costs decreased 60% in 2025" s1 0.85\n'
        '"Multi-agent adoption increased 300%" s2 0.90\n'
    ), [
        '#evid claim="LLM costs decreased 60% in 2025" src=s1 conf=0.85',
        '#evid claim="Multi-agent adoption increased 300%" src=s2 conf=0.90',
    ]),
    ("quota rows expand to key=value", (
        "#quota[type,total,used,rem]\n"
        "tokens 50000 38500 11500\n"
    ), [
        "#quota type=tokens total=50000 used=38500 rem=11500",
    ]),
    ("trailing @rid preserved on expansion", (
        "#evid[claim,src,conf]\n"
        '"x happened" s1 0.50 @rid=e1\n'
    ), [
        '#evid claim="x happened" src=s1 conf=0.50 @rid=e1',
    ]),
]


def main() -> None:
    print("PAIRL v1.5 columnar conformance (V12)")
    print("-" * 50)
    results = [check(*c) for c in CASES]
    print("  -- expansion / round-trip (§9.4a) --")
    results += [check_expansion(*c) for c in EXPANSION_CASES]
    print("-" * 50)
    passed, total = sum(results), len(results)
    print(f"{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
