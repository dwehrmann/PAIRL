# @pairl/pairl (TypeScript)

Reference library for the [PAIRL v1.5](../../SPEC.md) protocol: parse, serialize,
validate (rules V1–V12), canonicalize + SHA-256 hashing, and a deterministic
human-readable renderer. ESM, Node ≥ 18 (uses `node:crypto` for hashing).

## Install

```bash
npm install @pairl/pairl
```

## Usage

```ts
import { parse, validate, computeHash, render, encode, decode } from "@pairl/pairl";

const msg = decode(pairlText);          // = parse(pairlText)

const res = validate(msg);              // rules V1–V12
console.log(res.valid, res.errors, res.warnings);

console.log(computeHash(msg));          // canonical SHA-256 (columnar-invariant)
console.log(render(msg));               // faithful human-readable rendering
const text = encode(msg);               // Message AST -> canonical PAIRL text
```

Columnar blocks (`#evid[claim,src,conf]` + positional rows, §3.4) are parsed and
expanded to canonical `#type key=value` records, so a message **hashes
identically** in columnar or `key=value` form (§9.4a).

## Develop

```bash
npm install
npm run typecheck
npm test          # vitest
npm run build     # emit dist/
```
