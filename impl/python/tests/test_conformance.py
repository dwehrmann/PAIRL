"""Runs the shared cross-implementation conformance corpus (impl/conformance)."""

import unittest
from pathlib import Path

import pairl

CASES = Path(__file__).resolve().parents[2] / "conformance" / "cases.txt"


def load_cases():
    cases = []
    cur = None
    body: list[str] = []
    for line in CASES.read_text(encoding="utf-8").split("\n"):
        if line.startswith("@@@CASE "):
            if cur is not None:
                cases.append((*cur, "\n".join(body)))
            name, strict, valid, h, substr = line[len("@@@CASE "):].split("|", 4)
            cur = (name, strict == "1", valid == "1", h, substr)
            body = []
        elif cur is not None:
            body.append(line)
    if cur is not None:
        cases.append((*cur, "\n".join(body)))
    return cases


class TestConformance(unittest.TestCase):
    pass


def _make(name, strict, valid, h, substr, body):
    def t(self):
        msg = pairl.parse(body)
        res = pairl.validate(msg, strict=strict)
        self.assertEqual(res.valid, valid, f"{name}: valid={res.valid} errors={res.errors}")
        if not valid and substr != "-":
            self.assertTrue(any(substr in e for e in res.errors),
                            f"{name}: {substr!r} not in {res.errors}")
        if h != "-":
            self.assertEqual(pairl.compute_hash(msg), h, f"{name}: hash mismatch")
    return t


_cases = load_cases()
assert _cases, "conformance corpus is empty"
for _c in _cases:
    setattr(TestConformance, f"test_{_c[0]}", _make(*_c))


if __name__ == "__main__":
    unittest.main()
