# pairl (Python)

[![PyPI](https://img.shields.io/pypi/v/pairl.svg)](https://pypi.org/project/pairl/)
[![Python](https://img.shields.io/pypi/pyversions/pairl.svg)](https://pypi.org/project/pairl/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/dwehrmann/PAIRL/blob/main/LICENSE)

Reference implementation of **[PAIRL](https://pairl.dev)** — a compact,
human-readable, machine-parseable message format for agent-to-agent
communication. This package parses PAIRL, validates it (rules V1–V12),
canonicalizes and SHA-256–hashes it, and renders it back to human-readable
text. Pure standard library, no runtime dependencies.

## Why PAIRL?

Agents exchanging context in natural language burn tokens and let facts drift;
raw JSON is rigid and verbose. PAIRL separates a **lossy intent channel**
(tone, length, speech act) from a **lossless fact channel** (names, numbers,
evidence) and references large content instead of copying it.

| | Natural language | JSON | **PAIRL** |
|---|:---:|:---:|:---:|
| Token cost | high | medium–high | **low (≈40–90% less)** |
| Facts preserved losslessly | ✗ (drift) | ✓ | **✓ (dedicated channel)** |
| Tone/intent without verbosity | verbose | ✗ | **✓ (compact intents)** |
| Validatable on the wire | ✗ | schema | **✓ (V1–V12)** |
| Speaker/turn attribution in one body | ✗ | manual | **✓ (turn markers)** |
| Repeated records compacted | ✗ | ✗ | **✓ (columnar blocks)** |
| Content-addressable (stable hash) | ✗ | canonical JSON | **✓ (§9 + SHA-256)** |
| Human-renderable | ✓ | poor | **✓ (renderer)** |

## Protocol architecture

A PAIRL message is a **header block** (`@v`, `@id`, `@ts`, threading, budget, …)
followed by a blank line and **body records**:

- **Intents** — `req{t=topic,s=f,l=2}` — the *lossy* channel: speech act + style.
- **Lossless records** — `#fact`, `#ref`, `#evid`, `#rule` — exact data, treated
  as ground truth (never paraphrased).
- **Economic records** — `#cost`, `#quota` — native budget/usage tracking.
- **Tool records** — `#call`, `#ret`, `#think`, `#edit` — compact tool-use chains.
- **Turn markers** (v1.3) — `#u1`/`#a2` — attribute records to a speaker when a
  whole conversation is compressed into one body.
- **Columnar blocks** (v1.5) — `#evid[claim,src,conf]` + positional rows — declare
  a repeated key schema once instead of per record (~40% fewer tokens, lossless).

**Canonicalization & hashing (§9).** Columnar blocks expand to `#type key=value`
records before hashing, so a message produces the **same SHA-256** whether sent in
columnar or `key=value` form — enabling content-addressing, dedup, and caching.

## Install

```bash
pip install pairl
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

## CLI

```bash
python -m pairl validate [--strict] message.pairl   # exit 0 ok / 1 invalid
python -m pairl render   message.pairl
python -m pairl hash     message.pairl
python -m pairl canon    message.pairl
```

## Test

```bash
cd impl/python && python -m unittest discover -s tests
```

## Links

- **Specification:** <https://github.com/dwehrmann/PAIRL/blob/main/SPEC.md>
- **Repository & other implementations** (TypeScript, Rust) + shared conformance
  corpus: <https://github.com/dwehrmann/PAIRL/tree/main/impl>
- **Website:** <https://pairl.dev>

Licensed under Apache-2.0.
