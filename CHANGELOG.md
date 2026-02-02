# Changelog

All notable changes to the PAIRL specification will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- Updated canonicalization order to include `@budget` and `@limit` (§8.1)
- Extended intent registry with economic intents (§4.2)
- Updated error handling to include budget errors (§12.1)

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
- Header canonical order (§7.1)
- Intent arg normalization (§7.3)
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

### Planned for v1.2
- `#meta` record type for structured metadata
- `@priority` header for message prioritization
- Enhanced validation rules for multi-agent workflows
- Reference implementation in Python/TypeScript/Rust

### Under Consideration
- Compression hints for large message batches
- Streaming support for long-running tasks
- Multi-currency budget aggregation
- Time-based quota enforcement

---

## Version History Summary

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

---

For detailed specification, see [SPEC.md](SPEC.md).
