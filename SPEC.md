# PAIRL v1.5 — Protocol for Agent Intermediate Representation (Lite)

A compact, human-readable, machine-parseable agent-to-agent message format designed for:

* **Token efficiency** (short records, *short session-local message references* instead of long IDs, *columnar record blocks* that declare a key schema once instead of repeating it per record, pointers instead of copied context),
* **Reliability** (lossless facts + evidence + validation),
* **Economy** (native budget and quota management),
* **Tool-use compression** (compact representation of tool-call/result chains),
* **Interoperability** (works as payload anywhere; transport-agnostic),
* **Human endpoints** (render to natural language only when needed).

This spec defines:

1. Message headers + stable IDs
2. Records (lossy intents + lossless facts/refs/evidence + economic data + tool chains)
3. Canonicalization (stable hashing, diff-friendly)
4. Validation rules (anti-hallucination guardrails + budget compliance + tool chain integrity)
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

PAIRL messages are **atomic and immutable** once finalized. Each message represents a complete communication unit. Messages can reference other messages via `@p` and `@deps`, forming a DAG (directed acyclic graph) of communication.

### 0.4 In-Body Turn Attribution (v1.3)

Message-level threading (§2.2) attaches one header — including `@p`/`@deps` — to one communication unit. But a common use is compressing an **entire multi-turn conversation history into a single body** (e.g. a gateway encoding a chat transcript), where there is no per-turn header to say *who* spoke or *which turn* a record came from. Inferring the speaker from intent type and line order is lossy and causes **attribution drift** (records assigned to the wrong speaker, turns reordered).

v1.3 closes this with **in-body turn markers** (§3.3): a compact, header-free way to declare each turn's speaker and order inside the body. The canonical form is a single short token per turn — `#u1`, `#a2`, `#s3` (the letter is the speaker, the number is the order) — and records are attributed by **section grouping**: a record belongs to the most recent turn marker above it. This is the only PAIRL construct that carries a **speaker** — message headers identify and thread messages but never encode who authored them (that has been transport metadata).

Because a turn's speaker is structural metadata (it is known to whatever assembled the conversation), the marker SHOULD be assigned **deterministically by the encoder/gateway**, not inferred by a language model. Doing so removes attribution drift by construction. See §3.3.

### 0.5 Economy-First Design (v1.1)

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

### Example (v1.4):

```
@v 1
@id m3
@sid ref:sess:01JH0Q6Z7F8K4Q2S1R6E2E9A3B
@ts 2026-01-31T16:20:01.123+01:00
@p m2
@budget 0.10USD
@hash ref:hash:sha256:9c1a0f...e3

req{t=analysis,s=f,l=2,m=+,a=c} @rid=a1
#fact ask=market_analysis @rid=f1
#fact format=report @rid=f2
#ref input=ref:doc:sha256:9c1a... @rid=r1
#ref prior_brief=@m1#a1
#quota type=tokens total=100000 used=5000 rem=95000 @rid=q1
#cost val=0.02 cur=USD model=gpt-4o @rid=c1
```

`@id m3` is a **session-local** message id; `@sid` declares the thread's global
session id once. `@p m2` references the parent by its short id; `@root` is omitted
because the parent *is* the root's predecessor chain (see §2.2). `@m1#a1` is a
short record reference within the session. The long `ref:msg:<ULID>` form (v1.3) is
still accepted for cross-session/legacy references — see §10.

---

## 2. Header

Header lines start with `@`.

### 2.1 Required Header Fields

* `@v <int>` — protocol version. v1.x uses `1`.
* `@id <id>` — message identifier. In v1.4 this is a **session-local short id** (e.g. `m1`, `m4`), unique within its thread. Replaces v1.3's `@mid ref:msg:<ULID>`.
* `@ts <iso8601>` — timestamp with timezone offset and subsecond precision (milliseconds recommended).

> **Back-compat:** the long form `@mid ref:msg:<ULID>` (v1.3) is still accepted. A message MUST carry exactly one of `@id` or `@mid`. New messages SHOULD use `@id`.

### 2.2 Optional Header Fields (General)

**Threading (v1.4 short form — session-local ids):**

* `@sid <ref:sess:<ULID>>` — **session/thread id**, a globally-unique anchor declared **once on the root message** (descendants inherit it). Establishes the namespace that makes session-local `@id` values globally resolvable. OMIT for self-contained threads that need no cross-session addressing.
* `@p <id>` — direct predecessor's session-local id (reply/continuation). Replaces v1.3 `@parent`.
* `@root <id>` — root message's session-local id. **OMIT when the root is the parent** (i.e. `@p` already points at the root) — the common flat-thread case (§9.1a derivable-field rule).
* `@deps <id>,<id>` — additional dependency ids (DAG edges). **OMIT ids already given by `@p` or `@root`.**
* `@hash <ref:hash:sha256:...>` — integrity hash over canonicalized message bytes (unchanged).

> **Back-compat:** the long forms `@root`/`@parent`/`@deps` with `ref:msg:<ULID>` values (v1.3) remain valid and are used for cross-session edges (a dependency in another thread carries its own `@sid` namespace and is referenced fully-qualified — see §10).

### 2.3 Economic Header Fields (v1.1)

* `@budget <float><unit>` — Maximum budget for this task/subtree.
   * Examples: `0.05USD`, `10.00EUR`, `0.001BTC`
   * Unit: 3-letter currency code (ISO 4217) or custom unit
* `@limit <int><unit>` — Resource limit (tokens, API calls, time).
   * Examples: `5000t` (tokens), `10api` (API calls), `60s` (seconds)

### 2.4 Message ID Recommendations

**v1.4 — separate identity (cheap) from integrity (when needed).** Threading uses
short session-local ids; global uniqueness and integrity are added only where
required, instead of paying a 26-char ULID on every message reference.

* `@id` — short session-local token. Recommended alphabet base36 `[a-z0-9]`, 1–8 chars; a simple per-thread counter prefixed by a letter (`m1`, `m2`, …) is canonical. Must be unique within its thread.
* `@sid` — declare a **ULID** once per thread (on the root) when the thread must be addressable across sessions; descendants inherit it. A self-contained message/thread MAY omit `@sid` entirely.
* `@hash` = `sha256(canonical_message_bytes_without_@hash)` for immutability/audit (see §9.6) — add only where an audit trail is required.
* Rationale: a 26-char ULID repeated across `@mid`/`@root`/`@parent` and every record ref is the dominant structural overhead; short session-local ids remove it while `@sid`/`@hash` preserve global addressing and integrity exactly where they are actually used.

### 2.5 Timestamp Precision

* ISO 8601 format with timezone offset is required.
* Subsecond precision (milliseconds) is recommended but not required.
* Example: `2026-01-31T16:20:01.123+01:00`

---

## 3. Body Records

Records appear after the empty line. One logical record per line.

### 3.1 Record Types

PAIRL v1.5 defines:

**Turn marker (v1.3)**
* `#u1` / `#a2` / `#s3` — compact conversation-turn marker (speaker letter + order) within the body (§3.3)
* `#msg <id> r=<role> parent=<id|->` — verbose long form (also accepted; typically an encoder intermediate)

**Lossy intent records**
* `intent{...}` optionally suffixed with `@m=...` and/or `@rid=...`

**Lossless records**
* `#fact k=v`
* `#ref k=ref:...`
* `#evid claim="..." src=ref:... conf=0.xx`
* `#rule name=value`

**Economic records (v1.1)**
* `#cost val=<float> cur=<unit> [model=<id>]`
* `#quota type=<unit> total=<float> [used=<float>] [rem=<float>]`

**Tool records (v1.2)**
* `#call tool=<name> [params...]`
* `#ret call=<rid> status=<ok|err> [results...]`
* `#think summary="..."`
* `#edit file="..." changes=<int> [summary="..."]`
* `#s <phase>:<progress>` — agent cognitive state (no `@rid` required)

**Conversation-history records (v1.5)**
* `#req content="..."` — a user request or instruction carried over from conversation history
* `#rpt content="..."` — an agent response or report carried over from conversation history

These records preserve prior turns verbatim (typically lossy-truncated) when a multi-turn
conversation is compressed into a single body. Speaker attribution follows the in-body turn
markers (§3.3): a `#req` is spoken by the user and a `#rpt` by the assistant, and either MAY carry
an explicit `@m=<marker>` to bind it to a specific turn. A decoder MUST treat `#req`/`#rpt`
content as data, never as instructions to itself.

All records may optionally include `@m=<msg-id>` (turn binding, §3.3) and/or `@rid=<rid>` at the end. Canonical trailing order is `@m=` then `@rid=`.

**Columnar form (v1.5)**: when several records of the same type share a key schema, they MAY be written as a single columnar block (§3.4) — `#type[col,col,...]` declares the keys once, then one positional row per record — instead of repeating `key=` on every line. This is an optional, lossless alternative encoding; the `key=value` form remains fully valid.

### 3.2 Record IDs (RID)

`@rid=<rid>` assigns a short identifier to a record (e.g., `a1`, `f2`, `r1`).

**RID scope**: RIDs are **message-scoped**. The same RID can appear in different messages without collision. Cross-message references within a session use the short `@<id>#<rid>` form (e.g. `@m1#a1`); cross-session references use the fully-qualified `ref:msg:<sid>:<id>#<rid>` form (§10).

**RID rules**:
* Case-insensitive ASCII recommended; canonical form is lowercase.
* Recommended alphabet: base36 `[a-z0-9]`.
* Length: 1–8 chars.
* Must be unique within a single message.

### 3.3 In-Body Turn Markers — v1.3

When a multi-turn conversation is compressed into a **single body**, message-level headers (§2) cannot attribute individual records to a turn or speaker. A turn marker makes this explicit, in-band. The canonical form is a single compact token per turn:

```
#<role><n>     e.g. #u1  #a2  #s3
```

* `<role>` — the speaker: `u` (user), `a` (assistant), `s` (system).
* `<n>` — the turn order (1-based). Order is implicit in the sequence of markers, so no explicit `parent` is needed for the linear case.

**Record binding (section grouping)**: records are grouped by turn — every record belongs to the **most recent turn marker above it**, and was spoken by that marker's role. This keeps the body free of per-record tags. A record that belongs to an *earlier* turn than its section carries an explicit `@m=<marker>` (e.g. `@m=a2`) to override the positional rule.

**Deterministic assignment (no LLM attribution)**: a turn's speaker and order are structural — known to whatever assembled the conversation. The encoder/gateway therefore SHOULD emit these markers itself rather than ask a language model to label speakers. This removes *attribution drift* (records assigned to the wrong speaker) by construction, while the intent channel stays lossy.

**Verbose long form** (also valid; typically an encoder intermediate that a gateway rewrites into the compact form): `#msg <id> r=<role> parent=<prev-id|->`, where `<id>` is a body-scoped turn id, `r=` the role (and MAY name a participant id for multi-party, e.g. `r=staff_eng`), and `parent=` the preceding turn id (`-` for the first). Records bind to it by the same grouping rule, with `@m=<id>` as the override.

**Multi-party**: the compact `u`/`a`/`s` letters cover the common two-party + system case. For more participants, use the verbose `#msg` form with a named `r=` participant id.

#### Example — multi-turn history compressed into one body

```
#u1
req{t=db_migration,s=f,l=2,m=+,a=i} @rid=a1
#fact current_version=pg12 @rid=f1
#a2
pln{t=migration_strategy,s=f,l=2,m=+} @rid=a2
wrn{t=compatibility,s=f,l=1,m=!} @rid=a3
#fact tool=aws_dms @rid=f2
#fact risk=postgis_compatibility @rid=f3
#u3
qst{t=audit_log,s=f,l=1,m=0} @rid=a4
#fact audit_table=schema_audit_log @rid=f4
```

Here `tool=aws_dms` is unambiguously the assistant's (under `#a2`) and `audit_table` the user's (under `#u3`) — no speaker inference required, and no per-record tags needed.

### 3.4 Columnar Record Blocks — v1.5

When a message carries several records of the **same type that share a key schema** (e.g. five `#evid` rows, each with `claim`/`src`/`conf`), repeating the type tag and every `key=` on each line is pure structural overhead. A columnar block declares the schema once and lists the values positionally.

**Form**:

```
#<type>[<col1>,<col2>,…,<colN>]
<row>
<row>
…
```

* The **header** `#<type>[…]` names a record type with a **fixed key schema** (e.g. `evid` → `claim,src,conf`; `cost` → `val,cur,model,note`; `quota` → `type,total,used,rem`; tool records `call`/`ret`) and its **column order** as a comma-separated list of keys (no spaces).
* Each following **row** is one record: its space-separated fields map **positionally** to the declared columns. A row has exactly N fields for N columns.
* The block continues over consecutive lines and **ends** at the next line that starts with `#` (a new record or block header), a blank line, or the message terminator `---`.

A columnar row is **semantically identical** to the equivalent `key=value` record:

```
#evid[claim,src,conf]
"LLM costs decreased 60% in 2025" s1 0.85
"Multi-agent systems adoption increased 300%" s2 0.90
```

is exactly equivalent to:

```
#evid claim="LLM costs decreased 60% in 2025" src=s1 conf=0.85
#evid claim="Multi-agent systems adoption increased 300%" src=s2 conf=0.90
```

**Field rules** (these matter for unambiguous parsing):

* A field that contains spaces or special characters MUST be a **quoted string** (`"…"`, with `\"` escaping, per §8.2). Any number of columns may be quoted.
* A non-quoted field is an **atom** (§8.1) — it MUST NOT contain spaces.
* Therefore each row has exactly N fields once quoted strings are treated as single tokens; a row whose field count ≠ N is a validation error (V12).

**Per-row `@rid` / `@m=`**: a row MAY append `@m=` then `@rid=` after its positional fields (same trailing order as §3.1). Omit them unless the record is referenced — columnar blocks are the common case for *unreferenced* bulk records, so rows are usually tag-free.

**When it applies / when it doesn't**:

* Use it where the **same keys repeat** across records: `#evid`, `#cost`, `#quota`, and tool records — for `#call`/`#ret` only when the repeated calls actually share the same param/result keys (params vary per tool, so this typically means repeated calls to the *same* tool).
* It does **not** apply to records whose key is itself data, i.e. variable per line: `#fact key=value` (every `key` distinct) and `#ref refname=ref:…` (the ref name is the key). Keep those — and one-off `#rule`s — as `key=value`.

**Canonicalization**: columnar blocks are **expanded to their equivalent `#type key=value` records before canonicalization and hashing** (§9.4a). A message therefore hashes identically whether the sender used the columnar or the `key=value` form, so `@hash`, dedup, and caching are unaffected by the choice.

#### Example — the evidence/quota block above as columnar

```
#evid[claim,src,conf]
"LLM costs decreased 60% in 2025" s1 0.85
"Multi-agent systems adoption increased 300%" s2 0.90
"PAIRL adoption growing in enterprise" s3 0.75
#quota[type,total,used,rem]
tokens 50000 38500 11500
api_calls 25 18 7
```

---

## 4. Intents (Lossy Channel)

An intent is:

```
<intent>{<kvpairs>}
```

* `<intent>`:
   * **Core intent**: 2–4 chars, `[a-z0-9]{2,4}` (lowercase)
   * **Custom intent**: dotted namespace form, e.g. `org.acme.custom`
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

**Canonical key order** (see §9.3): `t,s,l,m,a,u,fmt`

**Speaker is not an intent parameter.** Intents describe *style and structure*, not who is speaking. The speaker/turn of an intent is given by the turn marker it sits under (§3.3), keeping the lossy channel free of attribution data.

### 4.1.1 Language Handling (Deliberate Omission)

**PAIRL does not include a `lang` parameter.**

Traditional protocols often tag content with language identifiers (e.g., `lang=de`, `lang=en`). PAIRL deliberately **omits this** for several reasons:

1. **Agent capability**: Modern LLMs are natively multilingual. Agent-to-agent communication does not require language tagging - agents understand content regardless of source language.

2. **Rendering concern, not protocol concern**: Language selection is a human-endpoint decision. When rendering PAIRL to natural language (§12), the renderer selects the appropriate output language based on user preference, not based on tags in the message.

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
* `fin` — complete/done
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
* For custom intents in multi-organization contexts, namespaced forms are allowed: `org.acme.custom{...}`
* Intent definitions may be versioned separately from the PAIRL protocol itself.

---

## 5. Lossless Records

### 5.1 `#fact` — Facts (Must Be Preserved)

```
#fact key=value [@rid=...]
```

**Rules**:
* `key` matches `[a-z][a-z0-9_]{0,31}`
* `value` is an atom or a quoted string (see §8).
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
#ref key=ref:<namespace>:<id> [@rid=...]
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
#ref prior=@m1#a2
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
#quota type=<unit> total=<float> [used=<float>] [rem=<float>] [@rid=...]
```

**Required keys**:
* `type` — resource type (e.g., `tokens`, `api_calls`, `seconds`)
* `total` — total allocated quota

**Optional keys**:
* `used` — amount used so far (optional for proposals/pre-execution messages)
* `rem` — remaining quota (can be computed: `rem = total - used`)

**Examples**:

```
#quota type=tokens total=100000 used=5000 rem=95000
#quota type=api_calls total=1000 used=42 rem=958
#quota type=seconds total=3600 used=120
```

---

## 7. Tool Records (v1.2)

Tool records capture **tool-use conversation history** in compressed form. In agentic workflows (Claude Code, Cursor, multi-agent systems), tools are invoked repeatedly — reading files, searching code, editing files, running commands. The raw tool-call/result messages consume 60-80% of context tokens, mostly from file contents and command output that are read-once.

Tool records compress this history into structured summaries while preserving the **decision chain**: what was called, what came back, and what reasoning led to the next action.

### 7.1 `#call` — Tool Invocation Record

Records a completed tool invocation with its key parameters.

Format:

```
#call tool=<name> [key=value ...] [@rid=...]
```

**Required keys**:
* `tool` — tool name (e.g., `Read`, `Grep`, `Edit`, `Bash`, `Glob`, `Write`)

**Optional keys**: Tool-specific parameters as additional key-value pairs. Encoders should include parameters that are essential for understanding the action (file paths, search patterns, commands) and omit verbose content (full file bodies, large outputs).

**Examples**:

```
#call tool=Read file="/src/app.ts" @rid=c01
#call tool=Grep pattern="handleProxy" path="/src/" @rid=c02
#call tool=Edit file="/src/proxy.ts" @rid=c03
#call tool=Bash cmd="npm test" @rid=c04
#call tool=Glob pattern="**/*.ts" @rid=c05
```

### 7.2 `#ret` — Tool Result Record

Records the compressed result of a tool invocation.

Format:

```
#ret call=<rid> status=<ok|err> [key=value ...] [@rid=...]
```

**Required keys**:
* `call` — RID of the corresponding `#call` record (back-reference)
* `status` — `ok` (success) or `err` (failure)

**Optional keys**: Result-specific summary data. Common patterns:

* `lines=<int>` — line count of file/output
* `matches=<int>` — number of search matches
* `files="<list>"` — matching files with locations
* `sig="<summary>"` — one-line content signature
* `summary="<text>"` — brief result description
* `exit=<int>` — command exit code
* `err="<text>"` — error message (when `status=err`)

**Examples**:

```
#ret call=c01 status=ok lines=450 sig="Hono HTTP app: auth middleware, proxy routes, billing" @rid=r01
#ret call=c02 status=ok matches=3 files="proxy.ts:161,proxy.ts:234,app.ts:558" @rid=r02
#ret call=c03 status=ok @rid=r03
#ret call=c04 status=ok summary="42 passed, 0 failed" exit=0 @rid=r04
#ret call=c05 status=ok matches=23 sig="TypeScript source files across src/ and lib/" @rid=r05
#ret call=c06 status=err err="File not found: /src/missing.ts" @rid=r06
```

**Linking**: `#ret` references its `#call` via the `call=` key, NOT by sharing the same `@rid`. This preserves V6 (RID uniqueness within a message).

### 7.3 `#think` — Reasoning Summary Record

Records a summarized reasoning step. In tool-use conversations, extended thinking blocks consume 15-20% of tokens but are irrelevant for subsequent turns. `#think` captures the essential decision in one line.

Format:

```
#think summary="<text>" [@rid=...]
```

**Required keys**:
* `summary` — quoted string describing the reasoning step

**Examples**:

```
#think summary="analyzed proxy code, identified SSE header stripping issue" @rid=t01
#think summary="file structure suggests monorepo with shared types package" @rid=t02
#think summary="test failures caused by missing env var, not code bug" @rid=t03
```

### 7.4 `#edit` — Aggregated Edit Record

Records multiple sequential edits to the same file, collapsed into a single summary. When an encoder detects repeated Edit→Read→Edit→Read cycles on the same file, it can aggregate them.

Format:

```
#edit file=<path> changes=<int> [summary="<text>"] [@rid=...]
```

**Required keys**:
* `file` — file path (quoted if contains spaces)
* `changes` — positive integer, number of individual edits aggregated

**Optional keys**:
* `summary` — quoted string describing the aggregate changes

**Examples**:

```
#edit file="/src/proxy.ts" changes=3 summary="added transfer-encoding strip, fixed SSE headers, added tool-use passthrough" @rid=d01
#edit file="/src/auth.ts" changes=5 summary="refactored session handling, added JWT validation" @rid=d02
#edit file="/tests/proxy.test.ts" changes=2 summary="added SSE streaming tests" @rid=d03
```

### 7.5 `#s` — State Token Record

Records the agent's current cognitive phase. When agentic conversations are compressed, the model's internal state (what it has decided, whether it's ready to act) gets lost. The `#s` token preserves this state so the model can resume without re-analyzing.

Format:

```
#s <phase>:<progress>
```

**Phase values**:
* `explore` — researching, reading files, gathering context
* `ready` — enough context collected, will act next
* `exec` — implementing changes
* `done` — task finished

**Progress** (optional): a ratio indicating how far along the phase is (e.g., `3/6` files read, `2/4` edits made).

**Examples**:

```
#s explore:3/6
#s ready:edit
#s exec:2/4
#s done
```

**Semantics**:
* Only the **most recent** `#s` token survives compression. Earlier state tokens are discarded.
* `#s` records do not require `@rid` (they are ephemeral, not referenceable).
* Encoders extract `#s` from assistant message text and emit it as a standalone record in the PAIRL body, positioned **after tool chain records** (at the end of the compressed section). This preserves chronological reading order: the model reads what actions were taken, then sees the resulting state.
* Encoders MUST only extract `#s` from the **old (compressed) region**, not from the recency window. If the most recent `#s` token is in the recent region, it already appears naturally in the preserved messages — injecting it again into the compressed body causes double-injection and can lead to action loops (e.g., models repeating completed deploys).
* The model emits `#s` tokens inline in its response text; encoders are responsible for extracting and preserving them.

### 7.6 Tool Chain Ordering

Tool records should appear in **chronological order** within the message body. A typical compressed session reads top-to-bottom as a narrative:

```
#think summary="need to find the proxy implementation" @rid=t01
#call tool=Grep pattern="handleProxy" path="/src/" @rid=c01
#ret  call=c01 status=ok matches=3 files="proxy.ts:161,proxy.ts:234,app.ts:558" @rid=r01
#call tool=Read file="/src/proxy.ts" @rid=c02
#ret  call=c02 status=ok lines=450 sig="proxy handler with SSE support" @rid=r02
#think summary="SSE headers being stripped by content-encoding logic" @rid=t02
#edit file="/src/proxy.ts" changes=2 summary="fixed SSE header stripping, added transfer-encoding handling" @rid=d01
#call tool=Bash cmd="npm test" @rid=c03
#ret  call=c03 status=ok summary="42 passed, 0 failed" exit=0 @rid=r03
#s done
```

Note: Only the **last** `#s` token survives compression (see §7.5). It is placed at the end of the tool chain, after all `#call`/`#ret`/`#edit` records. This ensures the model reads actions first, then the resulting state — preventing action loops where the model sees "done" before the actions that made it so.

### 7.7 Compression Strategy (Encoder Guidance)

This section provides guidance for encoders compressing tool-use conversations. These are **recommendations**, not protocol requirements.

**Recency Window**: Encoders should preserve the last W tool-use/tool-result message pairs as **original messages** (not compressed to records). Default W=3. This allows the model to:
* Maintain tool_use_id chains for continued tool calls
* Access concrete results from recent actions
* Continue the workflow without re-reading

**Older Pairs**: Tool interactions older than the recency window are compressed to `#call`/`#ret` records. The compression is lossy on content but lossless on structure.

**Thinking Blocks**: Extended thinking (`type: "thinking"`) should be:
* Within recency window: removed entirely (model just produced them)
* Older: compressed to `#think` records or removed

**Redundant Reads**: If the same file is read multiple times (e.g., after edits), only the last read's full result needs to be preserved. Earlier reads become `#call`/`#ret` records.

**Edit Aggregation**: Sequential edits to the same file within a turn should be aggregated into `#edit` records.

**Compressed Message Structure** (recommended):

```
Message 1 (system):    Original system prompt
Message 2 (user):      [PAIRL v1.2 Context]
                        <intent records>
                        <fact records>
                        <tool chain records>
Message 3 (assistant):  Understood.
Message 4+ (original):  Last W tool_use/tool_result pairs (verbatim)
Message N (user/asst):  Last message in conversation
```

---

## 8. Values and Quoting

### 8.1 Atoms

An atom is a value without spaces or special characters.

**Recommended charset**: `[A-Za-z0-9:._/@+-]+`

**Examples**: `spec_document`, `pdf_or_link`, `2026-02-05`, `high`, `ref:doc:sha256:...`, `0.05USD`

### 8.2 Quoted Strings

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

### 8.3 Minimal Grammar (Conformance Baseline)

The grammar below defines the minimum syntax strict parsers should accept.

```
message         := header-block LF body
header-block    := header-line *(LF header-line)
body            := *(record-line LF) [record-line]
header-line     := "@" hkey SP hval
record-line     := marker-record / msg-record / intent-record / hash-record / state-record / col-header / col-row

col-header      := "#" ident "[" key *("," key) "]"        ; v1.5 columnar block header, e.g. #evid[claim,src,conf]
col-row         := field *(SP field) [SP mtag] [SP rid]     ; one positional record; only valid inside a block
field           := atom / quoted

marker-record   := "#" ("u" / "a" / "s") 1*7(DIGIT)        ; compact turn marker, e.g. #u1
state-record    := "#s" SP atom                             ; v1.2 state token (§7.5), e.g. #s explore:3/6
msg-record      := "#msg" SP msgid SP "r=" role SP "parent=" (msgid / "-")  ; verbose long form
msgid           := 1*8(ALNUM)
role            := "u" / "a" / "s" / ident

intent-record   := intent-name ["{" kvpairs "}"] [SP mtag] [SP rid]
intent-name     := core-intent / custom-intent
core-intent     := 2*4(LOWER / DIGIT)
custom-intent   := ident "." ident *("." ident)

hash-record     := "#" ident SP kvpairs [SP mtag] [SP rid]
mtag            := "@m=" msgid
rid             := "@rid=" 1*8(ALNUM)
kvpairs         := kvpair *("," kvpair) / kvpair *(SP kvpair)
kvpair          := key "=" value
key             := LOWER *(LOWER / DIGIT / "_")
value           := atom / quoted
quoted          := DQUOTE *(%x20-21 / %x23-5B / %x5D-10FFFF / '\"') DQUOTE
atom            := 1*(ALNUM / ":" / "." / "_" / "/" / "@" / "+" / "-")

ref             := sloc-ref / short-ref / long-ref
sloc-ref        := "@" msgid ["#" ridfrag]                  ; v1.4 session-local msg/record ref, e.g. @m1 / @m1#a2
short-ref       := "ref:" ns ":" ridpart ["#" ridfrag]
long-ref        := "ref:" ns ":" rtype ":" ridpart ["#" ridfrag]  ; also the v1.4 fully-qualified form ref:msg:<sid>:<id>
ns              := ident
rtype           := ident
ridpart         := 1*(VCHAR - SP)
ridfrag         := 1*(ALNUM / "_" / "-")
deps-val        := ref *("," ref)
ident           := 1*(LOWER / DIGIT / "_" / "-")
```

Notes:
* `state-record` vs `marker-record`: `#s` followed directly by digits (`#s3`) is a turn marker; `#s` followed by a space and a payload atom (`#s done`, `#s explore:3/6`) is a state token. The state token has no `key=value` pair and is therefore *not* a `hash-record`.
* The conversation-history records `#req content="..."` / `#rpt content="..."` (v1.5, §3.1) need no dedicated production — they parse as `hash-record` (`#` ident SP kvpairs).
* `col-header` / `col-row` (v1.5, §3.4): a `col-header` opens a columnar block; every following line that is non-blank and does **not** start with `#` is a `col-row` belonging to that block. The block ends at the next line starting with `#`, a blank line, or `---`. Each `col-row` MUST have exactly as many fields (quoted strings count as one field) as the header has columns. Columnar blocks expand to `hash-record`s before canonicalization (§9.4a).
* `@deps` value uses `deps-val` (comma-separated refs, no spaces).
* `ref` permits `#<rid>` fragments for record references.
* v1.4 session-local refs use the `@<id>` / `@<id>#<rid>` form; cross-session refs use the fully-qualified `ref:msg:<sid>:<id>[#<rid>]` form (a `long-ref`).
* Both `ref:<ns>:<id>` and `ref:<ns>:<type>:<id>` are valid.
* Message identifiers (`@id`, and the ULID payload in `@sid`/legacy `ref:msg:<ULID>`) may contain uppercase.

---

## 9. Canonicalization (for Stable Hashing & Diff)

Canonicalization produces the canonical message used for:

* `@hash` calculation
* deterministic diffs
* caching/dedup

### 9.1 Header Canonical Order

Headers must appear in this order if present:

1. `@v`
2. `@id` (v1.4) / `@mid` (v1.3 long form)
3. `@sid` (v1.4)
4. `@ts`
5. `@root`
6. `@p` (v1.4) / `@parent` (v1.3 long form)
7. `@deps`
8. `@budget` (v1.1)
9. `@limit` (v1.1)
10. `@hash`

### 9.1a Derivable Threading Fields (v1.4)

To avoid redundant bytes, canonical v1.4 messages **OMIT threading fields whose value
is derivable**:

* OMIT `@root` when it is reachable by walking the `@p` chain (i.e. `@root` lies on the
  parent spine — the common case in any linear or tree thread). Keep `@root` only when a
  message attaches to the thread via `@deps` with no `@p` path to the root.
* OMIT from `@deps` any id already present as `@p` or `@root`.

A consumer reconstructs the omitted edges by walking `@p` to the root. These omissions
are canonical: a message and its de-duplicated form must hash identically, so the rule
is applied before §9.6.

### 9.2 Blank Line Rule

Exactly one empty line between header and body.

### 9.3 Intent Arg Normalization

Inside `{...}`:

* Remove redundant whitespace
* Normalize to `k=v` joined by commas with no spaces: `k=v,k2=v2`
* Order keys by: `t,s,l,m,a,u,fmt`
* Unknown keys (if allowed) come after known keys, sorted lexicographically

### 9.4 Record Formatting

* One record per line.
* Exactly one space before `@rid=...` if present.
* `#fact/#ref/#evid/#rule/#cost/#quota/#call/#ret/#think/#edit` fields use a single space between tokens:
   * `#fact key=value @rid=f1` (rid optional)
   * `#cost val=0.02 cur=USD @rid=c1`

### 9.4a Columnar Block Expansion (v1.5)

Before canonicalization, every columnar block (§3.4) is **expanded** to the equivalent sequence of `#type key=value` records: for header `#T[c1,…,cN]` and row `v1 … vN`, emit `#T c1=v1 … cN=vN` (preserving any trailing `@m=`/`@rid=`), in row order. A field that was a quoted string stays quoted; an atom stays unquoted. The expanded records are then formatted per §9.4.

Consequently a message hashes identically whether it was sent in columnar or `key=value` form — the columnar block is a transport-level encoding, not a distinct canonical object.

### 9.5 Line Endings

Use `\n` (LF). For hashing, canonical bytes are UTF-8 with LF line endings.

### 9.6 Hash Computation Rule (Non-Circular)

When computing `@hash`, canonicalize the message with **`@hash` omitted** from the header block.

Algorithm:

1. Parse message.
2. Remove `@hash` header if present.
3. Canonicalize per §9.1–§9.5.
4. Compute hash (recommended: SHA-256) over canonical UTF-8 bytes.
5. Encode as `@hash ref:hash:sha256:<hex>`.

Verification follows the same process: recompute from the message with `@hash` removed, then compare.

---

## 10. References (Message-Level and Record-Level)

PAIRL v1.4 has two reference scopes. Use the **short session-local** form by default;
fall back to the **fully-qualified** form only across session boundaries.

### 10.1 Session-Local References (default)

Within a thread, reference by short message id:

* Message: `@<id>` — e.g. `@m1`
* Record: `@<id>#<rid>` — e.g. `@m1#a2`

```
#ref reply_to=@m2#a2
```

These resolve within the current thread (the namespace established by `@sid` on the
root, or implicitly the self-contained thread).

### 10.2 Fully-Qualified References (cross-session)

To reference a message or record in **another** session, qualify with that session's id:

* Message: `ref:msg:<sid>:<id>` — e.g. `ref:msg:01JH0Q6Z7F8K...:m1`
* Record: `ref:msg:<sid>:<id>#<rid>` — e.g. `ref:msg:01JH0Q6Z7F8K...:m1#a2`

The v1.3 long form `ref:msg:<ULID>` / `ref:msg:<ULID>#<rid>` (where the ULID was the
message's own id) remains **accepted** for back-compatibility.

```
#ref upstream=ref:msg:01JH0Q6Z7F8K...:m1#a2
```

### 10.3 Reference Resolution

**PAIRL does not define a resolution protocol.** Reference resolution is a **transport-layer concern** or an **application-layer concern**.

**Implications**:
* PAIRL messages containing `ref:` pointers are valid even if refs cannot be resolved.
* Applications using PAIRL must implement their own ref resolution strategy (e.g., local store, distributed hash table, URL fetch).
* Unresolvable refs should be handled gracefully (see §13 Error Handling).

---

## 11. Validation Rules (v1.5)

PAIRL validators should support at least two modes:

* **loose**: warnings for best-effort interoperability
* **strict**: hard errors for production pipelines

### V1 — No-New-Facts (Policy Rule)

If enabled (via `#rule no_new_facts=true` or implementation policy):

* Intent records should not introduce new factual material.
* This is a **heuristic policy**, not a syntax rule.
* Strict conformance mode should parse valid intent parameters (including `l=0..3`, `m=0`) and apply V1 as a separate policy check.

**Practical heuristic checks** (recommended):
* Flag URLs (`http://`, `https://`) in intent values
* Flag long hash-like substrings (>= 12 hex chars) in intent values
* Optionally flag numeric values in non-standard keys (exclude known style keys such as `l`)
* Recommend moving suspicious factual content to `#fact` or `#ref`

### V2 — Evidence Completeness

Every `#evid` must include:

* `claim` (quoted)
* `src` (ref)
* `conf` (float 0..1)

### V3 — Ref Format

All refs must match one of:

* Session-local message/record ref (v1.4): `@<id>` or `@<id>#<rid>`
* Fully-qualified message/record ref (v1.4): `ref:msg:<sid>:<id>` or `ref:msg:<sid>:<id>#<rid>`
* Resource ref (short): `ref:<ns>:<id>`
* Resource ref (long): `ref:<ns>:<type>:<id>`
* Record reference form: any of the above with `#<rid>`
* v1.3 legacy: `ref:msg:<ULID>` / `ref:msg:<ULID>#<rid>` (accepted)
* No spaces in the ref value.
* `@deps` must be a comma-separated list of session-local `@<id>` values (or legacy refs for cross-session edges).

### V4 — Thread Integrity (Optional Strict)

If `@p` (or legacy `@parent`) is present and `strict_refs=true`:

* Referenced parent message must be resolvable in the thread (by session-local `@id`) or message store/log, otherwise error.

### V5 — Canonicalization Safety (Hash Mode)

If `@hash` is present:

* Recompute hash and compare; mismatch is an error.

### V6 — RID Uniqueness

Within a single message:

* All `@rid` values must be unique.
* Collision is an error.

### V7 — Circular Dependency Detection

If `@deps` or `@p` (or legacy `@parent`) create a cycle in the message DAG:

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
#ref budget_limit=@m1#budget @rid=r1

# Scenario 2: Budget check, bid for approval
bid{t=analysis,s=f,l=1} @rid=a1
#cost val=0.08 cur=USD note="estimated" @rid=c1
#quota type=tokens total=15000 @rid=q1
#fact wait_for_approval=true @rid=f1
```

### V9 — Tool Chain Integrity (v1.2)

If tool records are present:

* Every `#ret` must have a `call=` key whose value matches the `@rid` of a `#call` record in the same message.
* `#ret` `status` must be `ok` or `err`.
* `#call` without a matching `#ret` is valid (represents in-progress or result-stripped calls).
* `#edit` `changes` value must be a positive integer.
* `#think` must have a `summary=` key.

**Error behavior**:
* Orphaned `#ret` (no matching `#call`): error in strict mode, warning in loose mode.
* Invalid `status` value: error.
* Missing required keys (`tool` on `#call`, `call`/`status` on `#ret`, `file`/`changes` on `#edit`, `summary` on `#think`): error.

### V10 — State Token Validity (v1.2)

If `#s` records are present:

* `#s` must be followed by at least one non-whitespace token (the phase/progress value).
* `#s` records do not require `@rid`.
* Only the last `#s` record in a message is semantically meaningful; encoders should discard earlier ones.
* Lines starting with `#s ` in assistant messages are state tokens — encoders preserve them verbatim.

**Error behavior**:
* `#s` with no value after it: warning in loose mode, error in strict mode.
* Multiple `#s` records in encoded output: warning (only the last should survive).

### V11 — Turn Marker Integrity (v1.3)

If turn markers are present (compact `#u1`/`#a2`/`#s3` or verbose `#msg`):

* A compact marker must be `#<role><n>` with role in `u|a|s`; its id is `<role><n>` (e.g. `a2`).
* A verbose `#msg` must have a turn `<id>`, an `r=` role, and a `parent=` value.
* Turn ids must be unique within the body.
* `parent=` (verbose) must be `-` or reference a turn id declared in the same body, with no cycle (cf. V7).
* Any `@m=` on a record must reference a declared turn id.

**Error behavior**:
* Malformed marker, duplicate turn id, or dangling `@m=`/`parent=` reference: error.
* Record with no `@m=` while markers are in use: allowed (grouping/positional rule, §3.3).
* Turn markers do not require `@rid`.

### V12 — Columnar Block Integrity (v1.5)

If a columnar block (§3.4) is present:

* The header must match `#<type>[<key>,…]` — a fixed-schema `#`-record type (§3.4; not `#fact`/`#ref`, whose key is data) and a non-empty, comma-separated list of column keys (each a valid `key`, §8.3), with no duplicate column names.
* Every row in the block must have **exactly as many fields as the header declares columns**, where a quoted string counts as one field. Too few or too many fields: error.
* Fields containing spaces or special characters must be quoted (`\"` escaping); an unquoted field must be a valid atom (§8.1).
* After expansion (§9.4a), the resulting records must themselves satisfy that type's rules (e.g. an expanded `#evid` still requires `claim`/`src`/`conf`; V2 applies).
* Per-row `@m=`/`@rid=` follow the same rules as V6/V11.

**Error behavior**: malformed header, column-count mismatch, duplicate column key, or an unquoted field containing spaces: error.

---

## 12. Rendering Guideline (Human Endpoint)

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

## 13. Error Handling

### 13.1 Error Categories

PAIRL implementations should define error handling for:

1. **Syntax errors**: malformed headers, invalid record format
2. **Validation errors**: violation of rules V1-V12
3. **Resolution errors**: unresolvable `ref:` pointers
4. **Integrity errors**: hash mismatches, circular dependencies
5. **Budget errors** (v1.1): budget exceeded, invalid currency codes
6. **Tool chain errors** (v1.2): orphaned `#ret` records, missing required keys on tool records
7. **Columnar block errors** (v1.5): malformed block headers, per-row field-count mismatches (V12)

### 13.2 Error Modes

* **Strict mode**: halt processing on any error
* **Loose mode**: log warnings, attempt best-effort parsing
* **Partial parsing**: if enabled, extract valid records even from partially malformed messages

### 13.3 Recommended Error Behavior

* **Missing required headers** (`@v`, `@id`/`@mid`, `@ts`): hard error
* **Malformed records**: skip record, log warning (loose mode) or error (strict mode)
* **Unresolvable refs**: log warning, continue processing (resolution is out-of-scope)
* **Hash mismatch**: hard error (integrity violation)
* **RID collision**: hard error (ambiguous references)
* **Budget exceeded** (v1.1): log warning, expect `ref` or `bid` intent from agent
* **Orphaned `#ret`** (v1.2): error in strict mode, warning in loose mode
* **Missing tool record keys** (v1.2): error
* **Columnar block violations** (v1.5): error — malformed header, column-count mismatch, duplicate column key, unquoted field containing spaces (see V12)

### 13.4 Error Reporting

Implementations should provide structured error output including:

* Error code/category
* Line number (if applicable)
* Description
* Suggested fix (if available)

---

## 14. Versioning Strategy

### 14.1 Protocol Versioning

* PAIRL uses semantic versioning: `MAJOR.MINOR.PATCH`
* Current version: **1.5**
* `@v` header contains **major version only**

### 14.2 Version Compatibility

* **Backward compatibility**: v1.x parsers should accept v1.0 messages
* **Forward compatibility**: v1.0 parsers may reject v1.1 messages or parse them in degraded mode (ignoring `@budget`, `#cost`, `#quota`)
* **Breaking changes** require major version bump

### 14.3 Extension Points

New versions may:

* Add new intent types (backward compatible)
* Add new record types (e.g., `#note`, `#meta`) - requires minor version bump if parsers must understand them
* Change canonicalization rules (major version bump)
* Add new validation rules (minor version bump if optional, major if required)

### 14.4 Deprecation Policy

* Deprecated features must be documented
* Deprecation period: at least one major version
* Example: if `#rule` format changes in v2.0, v1.x format is still supported in v2.x but deprecated

### 14.5 v1.1 Changes

v1.1 adds:

* Economic headers: `@budget`, `@limit`
* Economic records: `#cost`, `#quota`
* Economic intents: `bid`, `ref` (refusal)
* Validation rule V8 (Budget Compliance)
* **Backward compatible**: v1.0 parsers can ignore v1.1 extensions

### 14.6 v1.2 Changes

v1.2 adds:

* Tool records: `#call`, `#ret`, `#think`, `#edit`
* State token: `#s` for agent cognitive state tracking (§7.5)
* Validation rules V9 (Tool Chain Integrity) and V10 (State Token Validity)
* Compression strategy guidance for tool-use conversations (§7.7)
* **Backward compatible**: v1.1 parsers can ignore v1.2 tool records and state tokens

### 14.7 v1.3 Changes

v1.3 adds:

* In-body turn markers for speaker + turn-order attribution inside a single body (§0.4, §3.3): compact `#u1`/`#a2`/`#s3` (canonical) and a verbose `#msg <id> r=<role> parent=<id|->` long form
* Section grouping: a record belongs to the most recent turn marker above it; `@m=<marker>` overrides
* The first PAIRL construct to carry a **speaker**; message headers thread but never authored
* Deterministic assignment: markers SHOULD be emitted by the encoder/gateway (speaker is structural), not inferred by an LLM — removing attribution drift by construction
* Validation rule V11 (Turn Marker Integrity)
* **Backward compatible**: v1.2 parsers can ignore turn markers and `@m=` tags; bodies without them are unchanged

### 14.8 v1.4 Changes

v1.4 shortens **agent-to-agent message references** to cut structural overhead (the
dominant cost on threaded traffic — a 26-char ULID was repeated across `@mid`,
`@root`, `@parent`, and every record ref):

* Session-local short message ids: `@id` (replaces `@mid ref:msg:<ULID>`), `@p` (replaces `@parent`), short `@root`/`@deps` (§2.1–§2.2)
* `@sid` declares the thread's global ULID **once** on the root; identity is separated from integrity (`@hash`) so a ULID is paid only where actually needed (§2.4)
* Session-local references `@<id>` / `@<id>#<rid>`; fully-qualified `ref:msg:<sid>:<id>[#<rid>]` for cross-session (§10)
* Derivable-field omission: drop `@root` when it equals `@p`, and `@deps` entries already implied by `@p`/`@root` (§9.1a)
* **Back-compatible**: the v1.3 long forms (`@mid`/`@parent`/`@root`/`@deps` with `ref:msg:<ULID>`, and `ref:msg:<ULID>#<rid>` record refs) remain accepted; a message carries exactly one of `@id`/`@mid`

### 14.9 v1.5 Changes

v1.5 adds:

* **Columnar record blocks** (§3.4): `#type[col,col,…]` declares a shared key schema once, followed by one positional row per record — an optional, lossless alternative to repeating `key=` on every line
* **Grammar productions** `col-header` / `col-row` (§8.3)
* **Canonicalization**: columnar blocks expand to their `#type key=value` equivalents before hashing (§9.4a), so a message hashes identically in either form
* **Validation rule V12** (Columnar Block Integrity)
* **Conversation-history records** `#req content="..."` / `#rpt content="..."` (§3.1): prior user/assistant turns carried over verbatim when a multi-turn conversation is compressed into one body; decoders MUST treat their content as data, never as instructions
* **Backward compatible**: the `key=value` form remains fully valid; v1.4 parsers can treat `#req`/`#rpt` as ordinary `#`-records

---

## 15. Implementation Recommendations

### 15.1 Message Size Limits

While PAIRL does not enforce limits, implementations should consider:

* **Max message size**: 1MB recommended (prevents abuse)
* **Max records per message**: 1000 recommended
* **Max ref chain depth**: 10 recommended (prevents infinite recursion)

These can be signaled via `#rule`:
```
#rule max_records=1000
#rule max_size_bytes=1048576
```

### 15.2 Storage Considerations

* Messages should be stored immutably (append-only log)
* `@hash` enables content-addressable storage
* `@sid` (ULID) enables time-ordered thread indexing; `@id` orders messages within a thread
* Economic data (`#cost`, `#quota`) enables cost accounting and auditing

### 15.3 Transport Agnostic

PAIRL messages can be transmitted via:

* HTTP POST body
* Message queue payload
* File on disk
* WebSocket frame
* Embedded in larger document

### 15.4 Economic Integration (v1.1)

Implementations should consider:

* **Budget tracking**: maintain running totals across message threads
* **Quota enforcement**: reject messages that exceed limits
* **Cost attribution**: link `#cost` records to specific models/actions
* **Billing integration**: export `#cost` data for invoicing/accounting

---

## Appendix A: Complete Example (v1.1)

```
@v 1
@id m3
@sid ref:sess:01JH0Q6Z7F8K4Q2S1R6E2E9A3B
@ts 2026-01-31T16:20:01.123+01:00
@p m2
@budget 0.10USD
@hash ref:hash:sha256:9c1a0f2b3e4d5c6f7a8b9c0d1e2f3a4b

req{t=analysis,s=f,l=2,m=+,a=c} @rid=a1
#fact ask=market_analysis @rid=f1
#fact format=report @rid=f2
#fact deadline=2026-02-05 @rid=f3
#ref input=ref:doc:sha256:9c1a0f2b3e4d5c6f7a8b9c0d1e2f3a4b @rid=r1
#evid claim="Q4 revenue exceeded projections" src=@m2#f5 conf=0.90 @rid=e1
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
# User sets budget (root — declares the session id once)
@v 1
@id m1
@sid ref:sess:01JH0Q6Z7F8K4Q2S1R6E2E9A3B
@ts 2026-01-31T10:00:00Z
@budget 0.50USD

req{t=research,s=f,l=2} @rid=a1
#fact topic=ai_trends_2026 @rid=f1

---

# Agent checks budget, proposes bid (@sid inherited; @root derivable via @p)
@v 1
@id m2
@p m1
@ts 2026-01-31T10:00:05Z

bid{t=research,s=f,l=1} @rid=a1
#cost val=0.35 cur=USD note="estimated: 3 sources + summary" @rid=c1
#quota type=tokens total=25000 @rid=q1
#fact wait_for_approval=true @rid=f1

---

# User approves, agent executes
@v 1
@id m3
@p m2
@ts 2026-01-31T10:01:00Z

ack{t=research} @rid=a1
#fact approved=true @rid=f1

---

# Agent reports results + actual cost
@v 1
@id m4
@p m3
@ts 2026-01-31T10:05:30Z

cmp{t=research,s=f,l=2} @rid=a1
#ref report=ref:doc:sha256:abc123... @rid=r1
#cost val=0.28 cur=USD model=gpt-4o note="actual cost" @rid=c1
#quota type=tokens total=25000 used=18500 rem=6500 @rid=q1
```

### C.2 Budget Exceeded Scenario

```
@v 1
@id m5
@p m1
@ts 2026-01-31T10:00:05Z

ref{t=research,m=-} @rid=a1
#fact reason=budget_exceeded @rid=f1
#cost val=0.75 cur=USD note="projected cost for comprehensive analysis" @rid=c1
#ref budget_limit=@m1#budget @rid=r1
```

---

## Appendix D: Tool-Use Compression Example (v1.2)

A compressed Claude Code session where an agent fixed SSE header handling in a proxy service:

```
@v 1
@id m7
@sid ref:sess:01JK9M2A3B4C5D6E7F8G9H0I1J2K
@ts 2026-02-25T14:30:00.000+01:00
@p m6

upd{t=proxy_fix,s=t,l=2,m=+,a=i} @rid=a1
#fact task="fix SSE header stripping in proxy service" @rid=f1
#fact status=completed @rid=f2
#fact tests_passed=42 @rid=f3
#think summary="need to find the proxy implementation" @rid=t01
#call tool=Grep pattern="handleProxy" path="/src/" @rid=c01
#ret  call=c01 status=ok matches=3 files="proxy.ts:161,proxy.ts:234,app.ts:558" @rid=r01
#call tool=Read file="/src/proxy.ts" @rid=c02
#ret  call=c02 status=ok lines=450 sig="proxy handler with SSE support, content-encoding logic" @rid=r02
#think summary="SSE headers being stripped by content-encoding normalization" @rid=t02
#call tool=Read file="/src/app.ts" @rid=c03
#ret  call=c03 status=ok lines=320 sig="Hono HTTP app: auth middleware, proxy routes, billing endpoints" @rid=r03
#edit file="/src/proxy.ts" changes=2 summary="skip content-encoding strip for SSE, preserve transfer-encoding" @rid=d01
#call tool=Bash cmd="npm test" @rid=c04
#ret  call=c04 status=ok summary="42 passed, 0 failed" exit=0 @rid=r04
#s done
#cost val=0.03 cur=USD model=claude-opus-4 @rid=k1
```

This represents ~20 turns of tool-use conversation (file reads, searches, edits, test runs) compressed to 18 records. The original conversation would have consumed ~15,000 tokens; the PAIRL representation uses ~800 tokens (~95% reduction).

---

**End of PAIRL v1.2 Specification**
