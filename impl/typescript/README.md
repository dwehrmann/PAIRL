# pairl (TypeScript)

[![npm](https://img.shields.io/npm/v/pairl.svg)](https://www.npmjs.com/package/pairl)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/dwehrmann/PAIRL/blob/main/LICENSE)

Reference library for **[PAIRL](https://pairl.dev)** — a compact, human-readable,
machine-parseable message format for agent-to-agent communication. Parse,
serialize, validate (rules V1–V12), canonicalize + SHA-256 hash, render, and
encode/decode. ESM; Node ≥ 18 (uses `node:crypto` for hashing).


## PAIRL v1.6

This release tracks spec v1.6 in lockstep. v1.6 adds **no new grammar** — the
extractive-quote and marked-condensate carriage forms for `#req`/`#rpt` live
inside ordinary quoted strings and kvpairs, so this parser handles v1.6 bodies
unchanged (two v1.6 cases are part of the conformance corpus). The new rules
V13–V15 are delivery-/encoder-side and out of message-parser scope by design
(SPEC §12a, §3.1/V15).

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
npm install pairl
```

## Usage

```ts
import { parse, validate, computeHash, render, encode, decode } from "pairl";

const msg = decode(pairlText);          // = parse(pairlText)

const res = validate(msg);              // rules V1–V12
console.log(res.valid, res.errors, res.warnings);

console.log(computeHash(msg));          // canonical SHA-256 (columnar-invariant)
console.log(render(msg));               // faithful human-readable rendering
const text = encode(msg);               // Message AST -> canonical PAIRL text
```

## API

| Function | Purpose |
|---|---|
| `parse(text)` / `decode(text)` | text → `Message` AST |
| `validate(msg, strict?)` | rules V1–V12 → `{ valid, errors, warnings }` |
| `computeHash(msg)` / `hashRef(msg)` | canonical SHA-256 (hex / `ref:hash:…`) |
| `canonicalize(msg)` / `encode(msg)` | `Message` → canonical PAIRL text |
| `render(msg)` | faithful human-readable rendering |

## Develop

```bash
npm install
npm run typecheck
npm test          # vitest
npm run build     # emit dist/
```

## Links

- **Specification:** <https://github.com/dwehrmann/PAIRL/blob/main/SPEC.md>
- **Repository & other implementations** (Python, Rust) + shared conformance
  corpus: <https://github.com/dwehrmann/PAIRL/tree/main/impl>
- **Website:** <https://pairl.dev>

Licensed under Apache-2.0.
