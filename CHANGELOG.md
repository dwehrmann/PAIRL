# Changelog

All notable changes to the PAIRL specification will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.5.0] - 2026-06-22

### Added

#### Columnar Record Blocks
- **`#type[col,col,…]` header + positional rows** (§3.4): when several records of the same type share a key schema, declare the keys once and list values positionally — `#evid[claim,src,conf]` then `"…" s1 0.85` — instead of repeating `claim=`/`src=`/`conf=` on every line. Optional, lossless alternative to the `key=value` form.
- **Field rules**: any field with spaces/special chars must be a quoted string (`\"` escaping, §8.2); unquoted fields are atoms; a row must have exactly as many fields as the header has columns.
- **Grammar** (§8.3): `col-header` and `col-row` productions; a block opens at a `#type[…]` header and ends at the next `#`-line, blank line, or `---`.
- **Validation rule V12** (Columnar Block Integrity): well-formed header, no duplicate column keys, exact per-row field count, quoting rules, and post-expansion type rules (e.g. expanded `#evid` still needs `claim`/`src`/`conf`).
- **Canonicalization** (§9.4a): columnar blocks expand to `#type key=value` records before hashing, so a message hashes identically in either form — `@hash`, dedup, and caching are unaffected.

### Rationale
- Measured on a real report message: scaffolding is ~90% of tokens and natural-language payload only ~10%. Declaring the schema once (dropping repeated keys) cut a representative message **43%** vs the verbose form, structurally lossless (deterministic round-trip), with no decoder fidelity loss in an isolated LLM probe (100% field-association accuracy, parity with `key=value`).

### Compatibility
- **Back-compat preserved**: the `key=value` record form (all prior versions) remains fully valid. Columnar is opt-in; decoders MUST accept both. Records with per-line distinct keys (`#fact`, one-off `#rule`) keep `key=value`.

---

## [1.4.0] - 2026-06-22

### Added

#### Session-Local Short References
- **Short ids**: `@id m2` / `@p m1` — session-local identifiers (`m1`, `m4`, …) unique within a thread, replacing v1.3's `@mid ref:msg:<ULID>` / `@parent`. Separates identity (cheap) from integrity (full content-hashes stay available via `@hash` / `#ref …sha256` when needed).
- **Global session anchor**: `@sid <ULID>` declared once on the root message; downstream messages reference it implicitly ("ULID only where needed").
- **Derivable-field elision** (§9.1a): `@root` MAY be omitted when reachable via the `@p` chain; `@deps` deduplicated against root/parent.
- **Record references**: `@m1#a1` (local) and `ref:msg:<sid>:<id>#<rid>` (fully-qualified cross-session).

### Changed
- §9.1 / §10: threading uses session-local short ids; cross-session edges carry their own `@sid` namespace and are referenced fully-qualified.

### Compatibility
- **Back-compat preserved**: the long forms `@mid ref:msg:<ULID>`, `@parent`, and `@root`/`@deps` with `ref:msg:<ULID>` values (v1.3) remain valid. A message MUST carry exactly one of `@id` or `@mid`; new messages SHOULD use `@id`.

---

## [1.3.0] - 2026-06-06

### Added

#### In-Body Turn Attribution
- **Compact turn markers**: `#u1` / `#a2` / `#s3` — declare a conversation turn *inside the body* (letter = speaker u/a/s, number = order), for the common case of compressing a multi-turn history into a single header-less body. The first PAIRL construct to encode who spoke; message headers thread messages but never authored them.
- **Section grouping**: a record belongs to the most recent turn marker above it and was spoken by that marker's role — no per-record tags in the common case. `@m=<marker>` (e.g. `@m=a2`) overrides for a cross-turn record.
- **Verbose long form**: `#msg <id> r=<role> parent=<id|->` is also valid (typically an encoder intermediate a gateway rewrites into the compact marker); supports named `r=` participant ids for multi-party.
- **Deterministic assignment**: markers SHOULD be emitted by the encoder/gateway (a turn's speaker is structural metadata), not inferred by a language model — removing attribution drift by construction.
- **Validation rule V11**: Turn Marker Integrity
  - Compact marker must be `#<role><n>` (role u/a/s); verbose `#msg` requires `r=` and `parent=`; turn ids unique within the body.
  - `parent=` and `@m=` must reference declared turn ids (no dangling refs); no `parent=` cycles.
  - A record without `@m=` is allowed (grouping rule); turn markers need no `@rid`.

### Changed
- §0.4 (new): rationale for in-body turn attribution vs. message-level threading; §0.5 = former Economy-First section.
- §3.1 / §3.3: turn-marker record types and full semantics + example.
- §4.1: speaker is deliberately *not* an intent parameter — it lives on the turn marker.
- §8.3 grammar: `marker-record`, `msg-record`, `mtag` (`@m=`), `role`, `msgid`.
- §3.2: canonical trailing order `@m=` then `@rid=`.

### Motivation
Compressing a transcript into one body dropped per-turn attribution, so decoders inferred the speaker from intent type + order — causing **attribution drift** (records reconstructed under the wrong speaker, turns reordered). Gateway-assigned turn markers make attribution deterministic and lossless while the intent channel stays lossy.

### Compatibility
- **Backward compatible**: v1.2 parsers ignore turn markers and `@m=` tags; bodies without them are unchanged.

---

## [1.2.1] - 2026-02-27

### Fixed

#### State Token (#s) Placement and Extraction
- **#s position**: Moved from "after facts, before tool records" to **after tool records**. Preserves chronological reading order so models read completed actions first, then the resulting state — prevents action loops where models see "done" before the actions that led to it.
- **#s extraction scope**: Encoders MUST only extract `#s` from the **old (compressed) region**, not from the recency window. If the most recent `#s` is in the recent region, it already appears in preserved messages. Double-injection caused models to repeat completed actions (e.g., deploying multiple times).

### Changed
- §7.5 Semantics: Updated placement rule and added extraction scope requirement
- §7.6 Example: Removed inline intermediate `#s` tokens, kept only final `#s done` at end of tool chain, added clarifying note
- Appendix D: Moved `#s done` from before tool records to after them

---

## [1.2.0] - 2026-02-25

### Added

#### Tool-Use Compression
- **Tool records**:
  - `#call` — tool invocation record (tool name + key parameters)
  - `#ret` — tool result summary (status + compressed results)
  - `#think` — summarized reasoning step
  - `#edit` — aggregated file edits (multiple edits collapsed)
- **State token**: `#s <phase>:<progress>` — agent cognitive state tracking
  - Phases: `explore`, `ready`, `exec`, `done`
  - Only the most recent `#s` survives compression
  - No `@rid` required (ephemeral, not referenceable)
- **Validation rule V9**: Tool Chain Integrity
  - `#ret` must reference valid `#call` RID via `call=` key
  - Status must be `ok` or `err`
  - Required keys enforced per record type
- **Validation rule V10**: State Token Validity
  - `#s` must be followed by a non-whitespace value
  - Only the last `#s` in encoded output is meaningful
- **Compression strategy guidance** (§7.7): recency window, edit aggregation, thinking removal

#### Documentation
- Section 7: Tool Records (§7.1–§7.8)
- Appendix D: Tool-Use Compression Example
- Example 06: Compressed tool-use session

### Changed
- Renumbered sections: §7 Values → §8, §8 Canon → §9, §9 Refs → §10, §10 Validation → §11, §11 Rendering → §12, §12 Errors → §13, §13 Versioning → §14, §14 Impl → §15
- Updated record formatting list to include tool records (§9.4)
- Updated error categories to include tool chain errors (§13.1)

### Backward Compatibility
- v1.2 is backward compatible with v1.1 and v1.0
- v1.1 parsers can safely ignore tool records (unknown `#` records)
- v1.2 parsers must accept v1.0/v1.1 messages without tool records

---

## [1.1.0] - 2026-02-01

### Added

#### Economic Features
- **Economic headers**: `@budget` and `@limit` for resource management
- **Economic records**:
  - `#cost` — cost reporting with currency, model ID, and notes
  - `#quota` — resource status tracking (tokens, API calls, time)
- **Economic intents**:
  - `bid` — propose resource needs before execution
  - `ref` — refusal/decline (e.g., insufficient budget)
- **Validation rule V8**: Budget Compliance
  - Agents must check projected costs against budget
  - Must refuse or bid for approval if budget exceeded
  - Should report actual costs after execution

#### Documentation
- Section 6: Economic Records (§6.1, §6.2)
- Section 14.4: Economic Integration recommendations
- Appendix C: Economic Use Cases with complete examples

### Changed
- Updated canonicalization order to include `@budget` and `@limit` (§9.1)
- Extended intent registry with economic intents (§4.2)
- Updated error handling to include budget errors (§13.1)

### Backward Compatibility
- v1.1 is backward compatible with v1.0
- v1.0 parsers can safely ignore v1.1 extensions (`@budget`, `#cost`, `#quota`)
- v1.1 parsers must accept v1.0 messages without economic features

---

## [1.0.0] - 2026-01-31

### Added

#### Core Protocol
- **Two-channel architecture**: Lossy intents + lossless facts
- **Message structure**: Headers (@v, @mid, @ts) + Records
- **Threading**: `@root`, `@parent`, `@deps` for DAG formation
- **Integrity**: `@hash` for content-addressable storage

#### Record Types
- **Lossy intents**: `req`, `qst`, `pln`, `sum`, `upd`, `cmp`, `jbl`, `wrn`, `ack`, `ctx`, `fnd`, `evl`, `lst`, `def`, `cnt`, `emf`, `agr`, `dis`, `alt`, `rpt`, `off`, `inc`, `fog`, `apx`, `thx`, `grt`, `cls`
- **Lossless records**:
  - `#fact` — facts that must be preserved
  - `#ref` — opaque pointers (ref:namespace:type:id)
  - `#evid` — claims with source attribution and confidence
  - `#rule` — on-the-wire constraints

#### Intent Parameters
- Style (`s`): formal, casual, trocken, poetisch, erhaben
- Length (`l`): 0-3 (ultra-short to longer)
- Mood (`m`): positive, negative, urgent, neutral
- Audience (`a`): internal, client, public
- Uncertainty (`u`): low, medium, high
- Format (`fmt`): paragraphs, bullets, numbered

#### Validation Rules
- **V1**: No-New-Facts (anti-hallucination)
- **V2**: Evidence completeness
- **V3**: Ref format validation
- **V4**: Thread integrity (optional strict)
- **V5**: Canonicalization safety (hash mode)
- **V6**: RID uniqueness
- **V7**: Circular dependency detection

#### Canonicalization
- Header canonical order (§9.1)
- Intent arg normalization (§9.3)
- Stable hashing for content-addressable storage
- Deterministic diffs

#### Documentation
- Complete specification (13 sections)
- File extensions: `.pairl`, `.prl`
- MIME type: `application/vnd.pairl+utf8`
- Rendering guidelines for human endpoints

### Design Decisions
- **No `lang` parameter**: Language is a rendering concern, not protocol concern (§4.1.1)
- **Pointer-first state**: Reference large content instead of copying
- **Transport-agnostic**: Works in HTTP, message queues, files, WebSocket
- **Human endpoints only**: Natural language rendering happens at final step

---

## [Unreleased]

### Planned for v1.3
- `#meta` record type for structured metadata
- `@priority` header for message prioritization
- Reference implementation in TypeScript/Rust

### Under Consideration
- Streaming support for long-running tasks
- Multi-currency budget aggregation
- Time-based quota enforcement
- Dynamic recency window sizing for tool-use compression

---

## Version History Summary

- **v1.2.1** (2026-02-27) — Fix #s state token placement and extraction scope (action loop prevention)
- **v1.2.0** (2026-02-25) — Tool-use compression (call, ret, think, edit) + state tokens (#s)
- **v1.1.0** (2026-02-01) — Economic features (budget, cost, quota)
- **v1.0.0** (2026-01-31) — Initial stable release

---

## Migration Guide

### From v1.0 to v1.1

**For Message Producers (Agents)**:
1. Optionally add `@budget` header if cost control needed
2. Optionally add `#cost` records to report actual spending
3. Optionally add `#quota` records to track resource usage
4. Use `bid` intent before expensive operations
5. Use `ref` intent to decline when budget exceeded

**For Message Consumers (Parsers)**:
1. Update canonicalization order to include `@budget` and `@limit`
2. Handle `#cost` and `#quota` records (or safely ignore them)
3. Implement V8 validation rule if strict budget enforcement needed
4. No breaking changes — all v1.0 messages remain valid

**Example v1.0 message** (still valid in v1.1):
```
@v 1
@mid ref:msg:01JH...
@ts 2026-01-31T16:20:01Z

req{t=task,s=f,l=2} @rid=a1
#fact id=123 @rid=f1
```

**Example v1.1 message** (with economic features):
```
@v 1
@mid ref:msg:01JH...
@ts 2026-01-31T16:20:01Z
@budget 0.10USD

req{t=task,s=f,l=2} @rid=a1
#fact id=123 @rid=f1
#cost val=0.02 cur=USD @rid=c1
#quota type=tokens used=5000 total=100000 @rid=q1
```

### From v1.1 to v1.2

**For Message Producers (Encoders)**:
1. Use `#call` records to capture tool invocations with key parameters
2. Use `#ret` records to summarize tool results (link via `call=<rid>`)
3. Use `#think` records to preserve reasoning summaries
4. Use `#edit` records to aggregate sequential file edits
5. Extract `#s` state tokens from assistant messages, preserve only the latest
6. Apply recency window strategy: keep last W pairs as original messages

**For Message Consumers (Parsers)**:
1. Handle `#call`, `#ret`, `#think`, `#edit`, `#s` records (or safely ignore them)
2. Implement V9/V10 validation rules if strict checking needed
3. Note renumbered sections (§7+ shifted by 1)
4. No breaking changes — all v1.0/v1.1 messages remain valid

---

For detailed specification, see [SPEC.md](SPEC.md).
