"""CLI: python -m pairl <validate|render|hash> [--strict] <file.pairl>"""

from __future__ import annotations

import sys

from . import canonicalize, compute_hash, parse, render, validate


def _usage() -> int:
    print("usage: python -m pairl <validate|render|hash|canon> [--strict] <file.pairl>")
    return 2


def main(argv: list[str]) -> int:
    args = argv[1:]
    if len(args) < 2:
        return _usage()
    cmd = args[0]
    strict = "--strict" in args
    files = [a for a in args[1:] if not a.startswith("-")]
    if not files:
        return _usage()
    path = files[0]

    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"error: {e}")
        return 2

    msg = parse(text)

    if cmd == "validate":
        res = validate(msg, strict=strict)
        for e in res.errors:
            print(f"  ✗ {e}")
        for w in res.warnings:
            print(f"  ⚠ {w}")
        print(f"{'✓ PASSED' if res.valid else '✗ FAILED'} — {path}")
        return 0 if res.valid else 1
    if cmd == "render":
        sys.stdout.write(render(msg))
        return 0
    if cmd == "hash":
        print(f"ref:hash:sha256:{compute_hash(msg)}")
        return 0
    if cmd == "canon":
        sys.stdout.write(canonicalize(msg, for_hash=not strict))
        return 0
    return _usage()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
