# PAIRL Conformance Corpus

A single, language-neutral set of test vectors that **all** reference
implementations run, so they provably agree on parsing, validation (V1–V12),
and canonical hashing.

## Format — `cases.txt`

Each case is a directive line followed by a verbatim PAIRL body:

```
@@@CASE <name>|<strict 0/1>|<valid 0/1>|<hash hex or ->|<expect-substr or ->
<PAIRL message body … until the next @@@CASE / EOF>
```

- **valid** — whether `validate()` must accept the message.
- **expect-substr** — for invalid cases, a substring that must appear in some error.
- **hash** — the canonical SHA-256 (SPEC §9). Implementations with a hasher
  (Python, TypeScript) assert it; the Rust validator (std-only, no hasher) skips it.

`evid_kv` and `evid_columnar` carry the **same** hash on purpose — columnar
invariance (§9.4a): a message hashes identically in `key=value` or columnar form.

## Runners

| Implementation | Test |
|---|---|
| Python | `impl/python/tests/test_conformance.py` |
| TypeScript | `impl/typescript/test/conformance.test.ts` |
| Rust | `impl/rust/tests/conformance.rs` |

## Updating

After changing the protocol or adding cases, regenerate the golden hashes from
the reference (Python) implementation and paste them into the `hash` fields, then
re-run all three runners.
