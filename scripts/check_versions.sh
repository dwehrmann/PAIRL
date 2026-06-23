#!/usr/bin/env bash
# Verifies that the three reference-implementation package versions agree,
# and (optionally) that they match an expected version — e.g. a pushed git tag.
#
# Usage:
#   scripts/check_versions.sh            # just check the three agree
#   scripts/check_versions.sh 1.5.1      # also require they equal 1.5.1
#   scripts/check_versions.sh v1.5.1     # leading "v" is stripped (git tag form)
#
# Note: this checks PACKAGE versions (package.json / pyproject.toml / Cargo.toml),
# which are released as a unit. The SPEC_VERSION constant ("1.5") is a separate,
# slower-moving concept and is intentionally not tied to the package version.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

extract() {
  # extract <file> <regex matching the version line>
  grep -oEm1 "$2" "$1" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1
}

ts=$(extract "$root/impl/typescript/package.json" '"version"[[:space:]]*:[[:space:]]*"[0-9.]+"')
py=$(extract "$root/impl/python/pyproject.toml"   '^version[[:space:]]*=[[:space:]]*"[0-9.]+"')
rs=$(extract "$root/impl/rust/Cargo.toml"         '^version[[:space:]]*=[[:space:]]*"[0-9.]+"')

echo "TypeScript (package.json): ${ts:-<none>}"
echo "Python     (pyproject.toml): ${py:-<none>}"
echo "Rust       (Cargo.toml):     ${rs:-<none>}"

fail=0
if [ -z "$ts" ] || [ -z "$py" ] || [ -z "$rs" ]; then
  echo "ERROR: could not extract one or more versions." >&2
  fail=1
fi

if [ "$ts" != "$py" ] || [ "$ts" != "$rs" ]; then
  echo "ERROR: package versions disagree (ts=$ts py=$py rs=$rs)." >&2
  fail=1
fi

if [ "$#" -ge 1 ]; then
  expected="${1#v}" # strip optional leading "v" (git tag form)
  if [ "$ts" != "$expected" ]; then
    echo "ERROR: package version ($ts) does not match expected ($expected)." >&2
    fail=1
  fi
fi

if [ "$fail" -ne 0 ]; then
  exit 1
fi

echo "OK: all package versions agree${1:+ and match ${1#v}}."
