# pairl-validator (Rust)

Reference parser and validator for the [PAIRL v1.5](../../SPEC.md) protocol —
rules V1–V12, including v1.3 turn markers, v1.4 short references, and v1.5
columnar record blocks. **Standard library only** (no dependencies), so it
builds and tests offline.

## CLI

```bash
cargo run --bin pairl-validate -- [--strict] message.pairl
# exit code 0 = valid, 1 = validation errors, 2 = usage/IO error
```

## Library

```rust
use pairl_validator::{parse, validate};

let msg = parse(&std::fs::read_to_string("message.pairl")?);
let res = validate(&msg, false); // strict = false
if res.valid() {
    println!("ok");
} else {
    for e in &res.errors { eprintln!("{e}"); }
}
```

The parser expands columnar blocks (`#evid[claim,src,conf]` + positional rows)
into per-record form, and V12 enforces header well-formedness, exact per-row
field counts, and the `#fact`/`#ref` columnar prohibition (key-is-data).

## Test

```bash
cargo test
```
