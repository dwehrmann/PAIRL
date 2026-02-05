# PAIRL v1.1 — Protocol for Agent Intermediate Representation (Lite)

A compact, human-readable, machine-parseable agent-to-agent message format designed for:

* **Token efficiency** (short records, pointers instead of copied context),
* **Reliability** (lossless facts + evidence + validation),
* **Economy** (native budget and quota management),
* **Interoperability** (works as payload anywhere; transport-agnostic),
* **Human endpoints** (render to natural language only when needed).

This spec defines:

1. Message headers + stable IDs
2. Records (lossy intents + lossless facts/refs/evidence + economic data)
3. Canonicalization (stable hashing, diff-friendly)
4. Validation rules (anti-hallucination guardrails + budget compliance)
5. Reference model for message- and record-level linking
6. Error handling
7. Versioning strategy

---

## 0. Core Ideas

### 0.1 Two Channels

PAIRL uses two complementary channels:

* **Lossy Intent channel**: short speech acts / "glue" (style, length, audience, intent). Example: `req{t=specs,s=f,l=2,m=+,a=c}`
* **Lossless channel**: facts, pointers, evidence, rules, and costs. Examples: `#fact format=pdf_or_link`, `#ref specs=ref:doc:sha256:...`, `#cost val=0.02 cur=USD`

**Rule of thumb**: Anything that must be correct later (names, numbers, IDs, dates, URLs, sources, costs) belongs in the lossless channel.

### 0.2 Pointer-First State

Large content should not be repeated in-line. Instead, reference it via `ref:` pointers.

### 0.3 Message Scope

PAIRL messages are **atomic and immutable** once finalized. Each message represents a complete communication unit. Messages can reference other messages via `@parent` and `@deps`, forming a DAG (directed acyclic graph) of communication.

### 0.4 Economy-First Design (v1.1)

PAIRL v1.1 introduces native support for **resource management**:

* **Budget tracking**: `@budget 0.10USD` sets maximum spend for a task
* **Quota monitoring**: `#quota type=tokens total=100000 used=5000` tracks resource usage
* **Cost reporting**: `#cost val=0.02 cur=USD model=gpt4` documents actual spending
* **Bidding**: `bid{...}` intent for agents to propose resource needs before execution

This enables **transparent, auditable resource management** in multi-agent systems.

---

## 1. Message Structure

A message is UTF-8 text with:

* a **Header block** (required fields + optional threading/hash),
* an **empty line**,
* a **Body**: a sequence of Records.

### Example (v1.1):

```
@v 1
@mid ref:msg:01JH0Q6Z7F8K4Q2S1R6E2E9A3B
@ts 2026-01-31T16:20:01.123+01:00
@root ref:msg:01JH0Q6YF1Z3QK...
@parent ref:msg:01JH0Q6X9R8...
@budget 0.10USD
@hash ref:hash:sha256:9c1a0f...e3

req{t=analysis,s=f,l=2,m=+,a=c} @rid=a1
#fact ask=market_analysis @rid=f1
#fact format=report @rid=f2
#ref input=ref:doc:sha256:9c1a... @rid=r1
#quota type=tokens total=100000 used=5000 rem=95000 @rid=q1
#cost val=0.02 cur=USD model=gpt-4o @rid=c1
```

---

## 2. Header

Header lines start with `@`.

### 2.1 Required Header Fields

* `@v <int>` — protocol version. v1.1 uses `1`.
* `@mid <ref>` — unique message identifier, must be `ref:msg:<id>`.
* `@ts <iso8601>` — timestamp with timezone offset and subsecond precision (milliseconds recommended).

### 2.2 Optional Header Fields (General)

* `@root <ref:msg:...>` — root message of the thread/job.
* `@parent <ref:msg:...>` — direct predecessor (reply/continuation).
* `@deps <ref:msg:...>,<ref:msg:...>` — additional dependencies (DAG edges).
* `@hash <ref:hash:sha256:...>` — integrity hash over canonicalized message bytes.

### 2.3 Economic Header Fields (v1.1)

* `@budget <float><unit>` — Maximum budget for this task/subtree.
   * Examples: `0.05USD`, `10.00EUR`, `0.001BTC`
   * Unit: 3-letter currency code (ISO 4217) or custom unit
* `@limit <int><unit>` — Resource limit (tokens, API calls, time).
   * Examples: `5000t` (tokens), `10api` (API calls), `60s` (seconds)

### 2.4 Message ID Recommendations

* Prefer **ULID** for `@mid` (sortable, collision-safe, 26 characters).
* Prefer `@hash` = `sha256(canonical_message_bytes)` for immutability/audit.
* Using `@mid` only is acceptable; using `@mid` + `@hash` is best practice.

### 2.5 Timestamp Precision

* ISO 8601 format with timezone offset is required.
* Subsecond precision (milliseconds) is recommended but not required.
* Example: `2026-01-31T16:20:01.123+01:00`

---

## 3. Body Records

Records appear after the empty line. One logical record per line.

### 3.1 Record Types

PAIRL v1.1 defines:

**Lossy intent records**
* `intent{...}` optionally suffixed with `@rid=...`

**Lossless records**
* `#fact k=v`
* `#ref k=ref:...`
* `#evid claim="..." src=ref:... conf=0.xx`
* `#rule name=value`

**Economic records (v1.1)**
* `#cost val=<float> cur=<unit> [model=<id>]`
* `#quota type=<unit> total=<float> used=<float> [rem=<float>]`

All records may optionally include `@rid=<rid>` at the end.

### 3.2 Record IDs (RID)

`@rid=<rid>` assigns a short identifier to a record (e.g., `a1`, `f2`, `r1`).

**RID scope**: RIDs are **message-scoped**. The same RID can appear in different messages without collision. Cross-message references use the full `ref:msg:<mid>#<rid>` format.

**RID rules**:
* Case-insensitive ASCII recommended; canonical form is lowercase.
* Recommended alphabet: base36 `[a-z0-9]`.
* Length: 1–8 chars.
* Must be unique within a single message.

---

## 4. Intents (Lossy Channel)

An intent is:

```
<intent>{<kvpairs>}
```

* `<intent>`: 2–4 chars, `[a-z0-9]{2,4}` (lowercase).
* `{}` is optional if no args, but recommended for uniformity.

### 4.1 Standard Intent Parameters (v1.1)

Parameters are comma-separated `k=v`.

**Keys**:

* `t` — topic/target (short identifier)
* `s` — style: `f|c|t|p|e`
   * `f` formal, `c` casual, `t` terse, `p` poetic, `e` elevated
* `l` — length: `0|1|2|3`
   * 0 ultra-short, 1 short, 2 normal, 3 longer
* `m` — mood: `+|-|!|0`
   * `+` positive, `-` negative, `!` urgent/strong, `0` neutral
* `a` — audience: `i|c|p`
   * `i` internal, `c` client, `p` public
* `u` — uncertainty: `lo|md|hi` (useful for reporting)
* `fmt` — formatting hint: `par|bul|num`
   * `par` paragraphs, `bul` bullets, `num` numbered list

**Canonical key order** (see §7.3): `t,s,l,m,a,u,fmt`

### 4.1.1 Language Handling (Deliberate Omission)

**PAIRL does not include a `lang` parameter.**

Traditional protocols often tag content with language identifiers (e.g., `lang=de`, `lang=en`). PAIRL deliberately **omits this** for several reasons:

1. **Agent capability**: Modern LLMs are natively multilingual. Agent-to-agent communication does not require language tagging - agents understand content regardless of source language.

2. **Rendering concern, not protocol concern**: Language selection is a human-endpoint decision. When rendering PAIRL to natural language (§10), the renderer selects the appropriate output language based on user preference, not based on tags in the message.

3. **Lossless channel is language-agnostic**: Facts, references, and evidence (`#fact`, `#ref`, `#evid`) encode language-neutral information (IDs, numbers, URLs, structured claims). When claims contain natural language, the language is implicit in the content itself.

4. **Lossy channel should stay lossy**: Intent parameters describe *style and structure*, not content semantics. Language would blur this boundary.

**Exception**: If preservation of source language is critical for a specific use case (e.g., legal documents, poetry), use a `#rule` to signal this to renderers:
```
#rule preserve_source_lang=true
```

**For human users**: We understand language feels important - humans think in languages! But in PAIRL's agent-to-agent layer, language is transparent. Your preferred language re-emerges automatically when the final agent renders the response for you.

### 4.2 Intent Registry (v1.1)

You can extend this registry in your implementation, but v1.1 commonly includes:

#### Workflow & State Management

* `ack` — acknowledge/confirm
* `req` — request/ask for something
* `qst` — ask a question
* `pln` — propose a plan / next steps
* `nxt` — next action (one-liner)
* `sum` — summarize
* `upd` — update/status report
* `cmp` — complete/done
* `hld` — hold/pause
* `blk` — blocked/waiting

#### Information & Analysis

* `ctx` — context/framing
* `fnd` — findings/results
* `evl` — evaluation/assessment
* `cmp` — comparison
* `lst` — list/enumeration
* `def` — definition/clarification

#### Stance & Rhetoric

* `jbl` — jubilation/proclamation (expressive)
* `wrn` — warn/risk note
* `cal` — calm/defuse
* `cnt` — contrast ("however...")
* `emf` — emphasis
* `agr` — agreement
* `dis` — disagreement
* `alt` — alternative/counter-proposal

#### Reporting & Attribution

* `rpt` — report (unconfirmed reporting, needs evidence)
* `off` — official statement / attribution
* `inc` — incident/event (neutral, confirmed by facts)
* `fog` — information unclear (optional; can be expressed as `ctx{u=hi}`)

#### Social/Interpersonal

* `apx` — apologize
* `thx` — thank
* `grt` — greet
* `cls` — close/goodbye

#### Economic (v1.1)

* `bid` — propose resource needs (tokens, cost, time) before execution
   * Example: `bid{t=analysis} #cost val=0.05 cur=USD #quota type=tokens total=10000`
* `ref` — refusal/decline (e.g., insufficient budget)
   * Example: `ref{t=analysis,m=-} #fact reason=budget_exceeded`

**Important**: Intents are lossy. They should not contain new factual claims. Use `#fact`/`#evid` for that.

### 4.3 Intent Registry Governance

* **Core intents** (§4.2) are standardized in this spec.
* **Custom intents** can be defined per-implementation or per-project.
* For custom intents in multi-organization contexts, consider namespacing: `org.acme.custom{...}`
* Intent definitions may be versioned separately from the PAIRL protocol itself.

---

## 5. Lossless Records

### 5.1 `#fact` — Facts (Must Be Preserved)

```
#fact key=value [@rid=...]
```

**Rules**:
* `key` matches `[a-z][a-z0-9_]{0,31}`
* `value` is an atom or a quoted string (see §6).
* Facts must be treated as authoritative by decoders/renderers.
* Use facts for: numbers, names, IDs, dates, URLs, amounts, locations, exact terms.

**Examples**:

```
#fact ask=spec_document
#fact format=pdf_or_link
#fact deadline=2026-02-05
#fact budget_eur=12000
#fact reason=budget_exceeded
```

### 5.2 `#ref` — Pointers (Opaque Handles)

Format:

```
#ref key=ref:<namespace>:<type>:<id> [@rid=...]
```

`ref:` is intentionally opaque to PAIRL parsers, but must be parseable by ref resolvers.

**Recommended ref patterns**:
* `ref:doc:sha256:<hex>`
* `ref:url:<url-or-encoded>`
* `ref:store:<kind>:<id>`
* `ref:msg:<id>` (message references)
* `ref:hash:sha256:<hex>`

**Examples**:

```
#ref specs=ref:doc:sha256:9c1a...
#ref source=ref:url:ap:2026-01-31
#ref parent=ref:msg:01JH0Q6...
#ref input=ref:doc:sha256:9c1a0f2b3e4d5c6f7a8b9c0d1e2f3a4b
```

### 5.3 `#evid` — Evidence/Claims with Attribution

Format:

```
#evid claim="..." src=ref:... conf=0.xx [@rid=...]
```

**Required keys**:
* `claim` (quoted string)
* `src` (ref)
* `conf` (0.00–1.00)

**Examples**:

```
#evid claim="multiple explosions reported" src=ref:url:ap:2026-01-31 conf=0.55
#evid claim="authorities attribute cause to accidents" src=ref:url:ap:2026-01-31 conf=0.70
```

### 5.4 `#rule` — On-the-Wire Constraints (Optional)

Format:

```
#rule name=value [@rid=...]
```

**Common rules**:
* `no_new_facts=true`
* `require_src_for_claims=true`
* `strict_refs=true`
* `preserve_source_lang=true`
* `max_records=<int>` (message size limit)

---

## 6. Economic Records (v1.1)

### 6.1 `#cost` — Cost Reporting

Format:

```
#cost val=<float> cur=<unit> [model=<id>] [note="..."] [@rid=...]
```

**Required keys**:
* `val` — numeric cost value (float)
* `cur` — currency or unit (3-letter code or custom)

**Optional keys**:
* `model` — model identifier (e.g., `gpt-4o`, `claude-opus-4`)
* `note` — explanation (quoted string)

**Examples**:

```
#cost val=0.02 cur=USD model=gpt-4o
#cost val=0.001 cur=USD model=gpt-4o-mini note="embeddings only"
#cost val=5000 cur=tokens
```

### 6.2 `#quota` — Resource Status

Format:

```
#quota type=<unit> total=<float> used=<float> [rem=<float>] [@rid=...]
```

**Required keys**:
* `type` — resource type (e.g., `tokens`, `api_calls`, `seconds`)
* `total` — total allocated quota
* `used` — amount used so far

**Optional keys**:
* `rem` — remaining quota (can be computed: `rem = total - used`)

**Examples**:

```
#quota type=tokens total=100000 used=5000 rem=95000
#quota type=api_calls total=1000 used=42 rem=958
#quota type=seconds total=3600 used=120
```

---

## 7. Values and Quoting

### 7.1 Atoms

An atom is a value without spaces or special characters.

**Recommended charset**: `[A-Za-z0-9:._/@+-]+`

**Examples**: `spec_document`, `pdf_or_link`, `2026-02-05`, `high`, `ref:doc:sha256:...`, `0.05USD`

### 7.2 Quoted Strings

Use double quotes when values contain spaces or special characters:

* `"like this"`
* Escape sequences: **only `\"` is escaped** as `\"` inside quoted strings.
* All other characters (including `\n`, `\t`, `\\`) are literal. If you need actual newlines or tabs in values, use literal characters, not escape sequences.
* Unicode characters are supported (UTF-8).

**Examples**:

```
#fact title="Project kickoff notes"
#evid claim="authorities attribute cause to accidents" src=ref:url:... conf=0.70
#cost note="includes both analysis and summarization"
```

---

## 8. Canonicalization (for Stable Hashing & Diff)

Canonicalization produces the canonical message used for:

* `@hash` calculation
* deterministic diffs
* caching/dedup

### 8.1 Header Canonical Order

Headers must appear in this order if present:

1. `@v`
2. `@mid`
3. `@ts`
4. `@root`
5. `@parent`
6. `@deps`
7. `@budget` (v1.1)
8. `@limit` (v1.1)
9. `@hash`

### 8.2 Blank Line Rule

Exactly one empty line between header and body.

### 8.3 Intent Arg Normalization

Inside `{...}`:

* Remove redundant whitespace
* Normalize to `k=v` joined by commas with no spaces: `k=v,k2=v2`
* Order keys by: `t,s,l,m,a,u,fmt`
* Unknown keys (if allowed) come after known keys, sorted lexicographically

### 8.4 Record Formatting

* One record per line.
* Exactly one space before `@rid=...` if present.
* `#fact/#ref/#evid/#rule/#cost/#quota` fields use a single space between tokens:
   * `#fact key=value @rid=f1` (rid optional)
   * `#cost val=0.02 cur=USD @rid=c1`

### 8.5 Line Endings

Use `\n` (LF). For hashing, canonical bytes are UTF-8 with LF line endings.

---

## 9. References (Message-Level and Record-Level)

### 9.1 Message References

A message is referenceable as:

* `ref:msg:<mid>`

### 9.2 Record References

A record is referenceable as:

* `ref:msg:<mid>#<rid>`

**Example**:

```
#ref reply_to=ref:msg:01JH0Q6Z7F...#a2
```

### 9.3 Reference Resolution

**PAIRL does not define a resolution protocol.** Reference resolution is a **transport-layer concern** or an **application-layer concern**.

**Implications**:
* PAIRL messages containing `ref:` pointers are valid even if refs cannot be resolved.
* Applications using PAIRL must implement their own ref resolution strategy (e.g., local store, distributed hash table, URL fetch).
* Unresolvable refs should be handled gracefully (see §12 Error Handling).

---

## 10. Validation Rules (v1.1)

PAIRL validators should support at least two modes:

* **loose**: warnings for best-effort interoperability
* **strict**: hard errors for production pipelines

### V1 — No-New-Facts (Core)

If enabled (via `#rule no_new_facts=true` or default strict policy):

* Intent records must not introduce new factual material.
* **Practical MVP checks (strict mode)**:
   * Reject digits in intent values (`\d`)
   * Reject `http://` or `https://` in intent values
   * Reject long hex-like substrings (≥12 hex chars)
   * Recommend moving them to `#fact` or `#ref`

(Heuristic by design; keep it simple and useful.)

### V2 — Evidence Completeness

Every `#evid` must include:

* `claim` (quoted)
* `src` (ref)
* `conf` (float 0..1)

### V3 — Ref Format

All refs must match:

* `ref:<ns>:<type>:<id>` (at minimum)
* No spaces in the ref value.

### V4 — Thread Integrity (Optional Strict)

If `@parent` is present and `strict_refs=true`:

* Referenced parent message must be resolvable in the message store/log, otherwise error.

### V5 — Canonicalization Safety (Hash Mode)

If `@hash` is present:

* Recompute hash and compare; mismatch is an error.

### V6 — RID Uniqueness

Within a single message:

* All `@rid` values must be unique.
* Collision is an error.

### V7 — Circular Dependency Detection

If `@deps` or `@parent` create a cycle in the message DAG:

* Error in strict mode.
* Warning in loose mode.

### V8 — Budget Compliance (v1.1)

If `@budget` is present:

* Before executing a task, agents should estimate projected cost
* If projected cost exceeds budget, agent MUST:
   * Either refuse with `ref` intent + `#fact reason=budget_exceeded`
   * Or send `bid` intent proposing resource needs and await approval
* After execution, agents SHOULD report actual cost via `#cost` record

**Recommended behavior**:

```
# Scenario 1: Budget exceeded, refusal
ref{t=analysis,m=-} @rid=a1
#fact reason=budget_exceeded @rid=f1
#cost val=0.08 cur=USD note="projected cost" @rid=c1
#ref budget_limit=ref:msg:01JH...#budget @rid=r1

# Scenario 2: Budget check, bid for approval
bid{t=analysis,s=f,l=1} @rid=a1
#cost val=0.08 cur=USD note="estimated" @rid=c1
#quota type=tokens total=15000 @rid=q1
#fact wait_for_approval=true @rid=f1
```

---

## 11. Rendering Guideline (Human Endpoint)

PAIRL is not primarily a natural language format. **Rendering is a separate step.**

**Recommended renderer behavior**:

* Use intents (`s,l,m,a,fmt`) as style/structure hints
* Always incorporate all `#fact` and `#evid` verbatim/faithfully
* Never add facts not present in lossless records
* When uncertainty exists, preserve attribution language:
   * `rpt` + `#evid` should render as "reported" / "according to ..."
* Language selection is based on **user preference**, not message content
* Renderers may maintain their own stylistic preferences but must not invent facts
* For economic data (`#cost`, `#quota`), display in human-readable format:
   * `#cost val=0.02 cur=USD` → "Cost: $0.02"
   * `#quota type=tokens used=5000 total=100000` → "Token usage: 5,000 / 100,000 (5%)"

---

## 12. Error Handling

### 12.1 Error Categories

PAIRL implementations should define error handling for:

1. **Syntax errors**: malformed headers, invalid record format
2. **Validation errors**: violation of rules V1-V8
3. **Resolution errors**: unresolvable `ref:` pointers
4. **Integrity errors**: hash mismatches, circular dependencies
5. **Budget errors** (v1.1): budget exceeded, invalid currency codes

### 12.2 Error Modes

* **Strict mode**: halt processing on any error
* **Loose mode**: log warnings, attempt best-effort parsing
* **Partial parsing**: if enabled, extract valid records even from partially malformed messages

### 12.3 Recommended Error Behavior

* **Missing required headers** (`@v`, `@mid`, `@ts`): hard error
* **Malformed records**: skip record, log warning (loose mode) or error (strict mode)
* **Unresolvable refs**: log warning, continue processing (resolution is out-of-scope)
* **Hash mismatch**: hard error (integrity violation)
* **RID collision**: hard error (ambiguous references)
* **Budget exceeded** (v1.1): log warning, expect `ref` or `bid` intent from agent

### 12.4 Error Reporting

Implementations should provide structured error output including:

* Error code/category
* Line number (if applicable)
* Description
* Suggested fix (if available)

---

## 13. Versioning Strategy

### 13.1 Protocol Versioning

* PAIRL uses semantic versioning: `MAJOR.MINOR.PATCH`
* Current version: **1.1**
* `@v` header contains **major version only**

### 13.2 Version Compatibility

* **Backward compatibility**: v1.x parsers should accept v1.0 messages
* **Forward compatibility**: v1.0 parsers may reject v1.1 messages or parse them in degraded mode (ignoring `@budget`, `#cost`, `#quota`)
* **Breaking changes** require major version bump

### 13.3 Extension Points

New versions may:

* Add new intent types (backward compatible)
* Add new record types (e.g., `#note`, `#meta`) - requires minor version bump if parsers must understand them
* Change canonicalization rules (major version bump)
* Add new validation rules (minor version bump if optional, major if required)

### 13.4 Deprecation Policy

* Deprecated features must be documented
* Deprecation period: at least one major version
* Example: if `#rule` format changes in v2.0, v1.x format is still supported in v2.x but deprecated

### 13.5 v1.1 Changes

v1.1 adds:

* Economic headers: `@budget`, `@limit`
* Economic records: `#cost`, `#quota`
* Economic intents: `bid`, `ref` (refusal)
* Validation rule V8 (Budget Compliance)
* **Backward compatible**: v1.0 parsers can ignore v1.1 extensions

---

## 14. Implementation Recommendations

### 14.1 Message Size Limits

While PAIRL does not enforce limits, implementations should consider:

* **Max message size**: 1MB recommended (prevents abuse)
* **Max records per message**: 1000 recommended
* **Max ref chain depth**: 10 recommended (prevents infinite recursion)

These can be signaled via `#rule`:
```
#rule max_records=1000
#rule max_size_bytes=1048576
```

### 14.2 Storage Considerations

* Messages should be stored immutably (append-only log)
* `@hash` enables content-addressable storage
* `@mid` (ULID) enables time-ordered indexing
* Economic data (`#cost`, `#quota`) enables cost accounting and auditing

### 14.3 Transport Agnostic

PAIRL messages can be transmitted via:

* HTTP POST body
* Message queue payload
* File on disk
* WebSocket frame
* Embedded in larger document

### 14.4 Economic Integration (v1.1)

Implementations should consider:

* **Budget tracking**: maintain running totals across message threads
* **Quota enforcement**: reject messages that exceed limits
* **Cost attribution**: link `#cost` records to specific models/actions
* **Billing integration**: export `#cost` data for invoicing/accounting

---

## Appendix A: Complete Example (v1.1)

```
@v 1
@mid ref:msg:01JH0Q6Z7F8K4Q2S1R6E2E9A3B
@ts 2026-01-31T16:20:01.123+01:00
@root ref:msg:01JH0Q6YF1Z3QK9P8M7N6L5K4J
@parent ref:msg:01JH0Q6X9R8S7T6U5V4W3X2Y1Z
@budget 0.10USD
@hash ref:hash:sha256:9c1a0f2b3e4d5c6f7a8b9c0d1e2f3a4b

req{t=analysis,s=f,l=2,m=+,a=c} @rid=a1
#fact ask=market_analysis @rid=f1
#fact format=report @rid=f2
#fact deadline=2026-02-05 @rid=f3
#ref input=ref:doc:sha256:9c1a0f2b3e4d5c6f7a8b9c0d1e2f3a4b @rid=r1
#evid claim="Q4 revenue exceeded projections" src=ref:msg:01JH0Q6X9R8S7T6U5V4W3X2Y1Z#f5 conf=0.90 @rid=e1
#quota type=tokens total=100000 used=5000 rem=95000 @rid=q1
#cost val=0.02 cur=USD model=gpt-4o @rid=c1
#rule no_new_facts=true @rid=x1
```

---

## Appendix B: File Extensions

Recommended file extensions for PAIRL messages:

* `.pairl` — primary extension
* `.prl` — short alternative

MIME type (proposed): `application/vnd.pairl+utf8`

---

## Appendix C: Economic Use Cases (v1.1)

### C.1 Budget-Constrained Research

```
# User sets budget
@v 1
@mid ref:msg:01JH...A
@ts 2026-01-31T10:00:00Z
@budget 0.50USD

req{t=research,s=f,l=2} @rid=a1
#fact topic=ai_trends_2026 @rid=f1

---

# Agent checks budget, proposes bid
@v 1
@mid ref:msg:01JH...B
@parent ref:msg:01JH...A
@ts 2026-01-31T10:00:05Z

bid{t=research,s=f,l=1} @rid=a1
#cost val=0.35 cur=USD note="estimated: 3 sources + summary" @rid=c1
#quota type=tokens total=25000 @rid=q1
#fact wait_for_approval=true @rid=f1

---

# User approves, agent executes
@v 1
@mid ref:msg:01JH...C
@parent ref:msg:01JH...B
@ts 2026-01-31T10:01:00Z

ack{t=research} @rid=a1
#fact approved=true @rid=f1

---

# Agent reports results + actual cost
@v 1
@mid ref:msg:01JH...D
@parent ref:msg:01JH...C
@ts 2026-01-31T10:05:30Z

cmp{t=research,s=f,l=2} @rid=a1
#ref report=ref:doc:sha256:abc123... @rid=r1
#cost val=0.28 cur=USD model=gpt-4o note="actual cost" @rid=c1
#quota type=tokens total=25000 used=18500 rem=6500 @rid=q1
```

### C.2 Budget Exceeded Scenario

```
@v 1
@mid ref:msg:01JH...E
@parent ref:msg:01JH...A
@ts 2026-01-31T10:00:05Z

ref{t=research,m=-} @rid=a1
#fact reason=budget_exceeded @rid=f1
#cost val=0.75 cur=USD note="projected cost for comprehensive analysis" @rid=c1
#ref budget_limit=ref:msg:01JH...A#budget @rid=r1
```

---

**End of PAIRL v1.1 Specification**
