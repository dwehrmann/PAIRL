# PAIRL Reference Implementations

Reference implementations of the [PAIRL v1.5](../SPEC.md) protocol in three
languages. All parse the same grammar (headers, intents, lossless/economic/tool
records, v1.3 turn markers, v1.4 short references, v1.5 columnar blocks) and
enforce the same validation rules (V1–V12). They agree on all files in
[`../examples`](../examples).

| Dir | Language | Scope | Tests |
|-----|----------|-------|-------|
| [`python/`](python) | Python ≥3.10 (stdlib) | parser · validator · canonicalize+SHA-256 · NL renderer · CLI | `python -m unittest` (29) |
| [`typescript/`](typescript) | TypeScript / Node ≥18 (ESM) | parse · serialize · validate · canonicalize+SHA-256 · render · encode/decode | `vitest` (29) |
| [`rust/`](rust) | Rust 2021 (stdlib only) | parser · validator (V1–V12) · CLI | `cargo test` (12) |

Each test count includes the shared [`conformance/`](conformance) corpus that all
three run (14 vectors), so the implementations are verified to agree on validity,
error reporting, and — for Python/TypeScript — the canonical SHA-256 hashes.

## Shared guarantees

- **Columnar invariance (§9.4a):** the Python and TypeScript canonicalizers
  expand `#type[col,…]` columnar blocks to `#type key=value` records before
  hashing, so a message produces the **same SHA-256** in either form.
- **Validation parity:** the same rule set (V1–V12) across implementations;
  columnar integrity (V12) and the `#fact`/`#ref` columnar prohibition are
  enforced everywhere.

## Quick check

```bash
# Python
cd python && python -m unittest discover -s tests

# TypeScript
cd typescript && npm install && npm test

# Rust
cd rust && cargo test
```
