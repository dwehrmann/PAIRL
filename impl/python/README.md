# pairl (Python)

Reference implementation of the [PAIRL v1.5](../../SPEC.md) protocol: parser,
validator (rules V1–V12), canonicalizer + SHA-256 hashing, and a deterministic
human-readable renderer. Pure standard library, no runtime dependencies.

## Install

```bash
pip install -e impl/python      # from the repo root
```

## Library

```python
import pairl

msg = pairl.parse(open("message.pairl").read())

res = pairl.validate(msg)            # rules V1–V12
print(res.valid, res.errors, res.warnings)

print(pairl.compute_hash(msg))       # canonical SHA-256 (columnar-invariant)
print(pairl.render(msg))             # faithful human-readable rendering
```

Columnar blocks (`#evid[claim,src,conf]` + positional rows, §3.4) are parsed and
expanded to their canonical `#type key=value` records, so a message **hashes
identically** whether sent in columnar or `key=value` form (§9.4a).

## CLI

```bash
python -m pairl validate [--strict] message.pairl
python -m pairl render   message.pairl
python -m pairl hash     message.pairl
python -m pairl canon    message.pairl
```

## Test

```bash
cd impl/python && python -m unittest discover -s tests
```
