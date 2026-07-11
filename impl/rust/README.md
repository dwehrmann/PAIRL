# pairl (Rust)

[![crates.io](https://img.shields.io/crates/v/pairl.svg)](https://crates.io/crates/pairl)
[![docs.rs](https://docs.rs/pairl/badge.svg)](https://docs.rs/pairl)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/dwehrmann/PAIRL/blob/main/LICENSE)

Reference parser and validator for **[PAIRL](https://pairl.dev)** — a compact,
human-readable, machine-parseable message format for agent-to-agent
communication. Validates rules V1–V12, including v1.3 turn markers, v1.4 short
references, and v1.5 columnar record blocks. **Standard library only** (no
dependencies), so it builds and tests offline.


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

This crate parses all of the above and enforces the conformance rules (V1–V12),
including columnar integrity (V12) and the `#fact`/`#ref` columnar prohibition
(their key is data, not a shared schema). It has no canonical hasher; the Python
and TypeScript implementations cover canonicalization + SHA-256.

## Install

```bash
cargo add pairl
```

## Library

```rust
use pairl::{parse, validate};

let msg = parse(&std::fs::read_to_string("message.pairl")?);
let res = validate(&msg, false); // strict = false
if res.valid() {
    println!("ok");
} else {
    for e in &res.errors { eprintln!("{e}"); }
}
```

## CLI

```bash
cargo run --bin pairl-validate -- [--strict] message.pairl
# exit 0 = valid, 1 = validation errors, 2 = usage/IO error
```

## Test

```bash
cargo test
```

## Links

- **Specification:** <https://github.com/dwehrmann/PAIRL/blob/main/SPEC.md>
- **Repository & other implementations** (Python, TypeScript) + shared
  conformance corpus: <https://github.com/dwehrmann/PAIRL/tree/main/impl>
- **Website:** <https://pairl.dev>

Licensed under Apache-2.0.
