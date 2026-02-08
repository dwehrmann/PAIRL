# PAIRL — Protocol for Agent Intermediate Representation (Lite)

**Version 1.1** | [Specification](SPEC.md) | [Examples](examples/) | [Contributing](CONTRIBUTING.md) | [Website](https://pairl.dev)

---

## Overview

PAIRL is a compact, human-readable, machine-parseable message format for **agent-to-agent communication**.

Instead of verbose natural language between AI agents, PAIRL uses:

* **Two channels**: lossy intents (style/mood) + lossless facts (names, numbers, evidence)
* **Pointer-first state**: references instead of copying large content
* **Token efficiency**: 70-90% reduction vs natural language
* **Economic features** (v1.1): native budget tracking, cost reporting, quota management
* **Anti-hallucination guardrails**: strict separation of facts from style
* **Transport-agnostic**: works anywhere (HTTP, files, message queues, WebSocket)

---

## Quick Example

```
@v 1
@mid ref:msg:01JH0Q6Z7F8K4Q2S1R6E2E9A3B
@ts 2026-01-31T16:20:01.123+01:00

req{t=specs,s=f,l=2,m=+,a=c} @rid=a1
#fact ask=spec_document @rid=f1
#fact format=pdf_or_link @rid=f2
#fact deadline=2026-02-05 @rid=f3
#ref specs=ref:doc:sha256:9c1a0f2b3e4d5c6f7a8b9c0d1e2f3a4b @rid=r1
```

**What this says**:
* **Lossy intent** (`req`): "I'm making a formal request about specs, medium length, positive mood, for client audience"
* **Lossless facts**: deadline is 2026-02-05, format is pdf or link, asking for spec_document
* **Reference**: points to document by content hash instead of copying it

See [examples/](examples/) for complete threaded conversations.

---

## Why PAIRL?

### Problem: Agent Verbosity

When AI agents talk to each other using natural language:

* **Token waste**: "According to the document you provided..." instead of `ref:doc:sha256:...`
* **Hallucination risk**: facts mixed with style/prose
* **Parsing overhead**: LLMs must re-parse generated prose
* **Context limits**: verbose messages burn context windows

### Solution: Structured Intermediate Format

PAIRL gives agents a **compact wire format** while preserving natural language for humans:

```
Agent A --> [PAIRL message] --> Agent B
                                    ↓
                            [PAIRL renderer]
                                    ↓
                                 Human
```

**Natural language only appears at the final human endpoint.**

---

## Core Principles

### 1. Two Channels

* **Lossy channel**: intents like `req{t=specs,s=f,l=2}` (style, mood, audience)
* **Lossless channel**: `#fact`, `#ref`, `#evid` (facts, pointers, evidence)

**Rule**: Anything that must be correct later (names, numbers, dates, URLs) goes in the lossless channel.

### 2. Pointer-First State

Don't copy large content. Reference it:

```
#ref doc=ref:doc:sha256:9c1a0f2b3e4d5c6f7a8b9c0d1e2f3a4b
```

### 3. Message Threading

Messages form a DAG (directed acyclic graph):

```
@root ref:msg:01JH0Q6YF1Z3QK9P8M7N6L5K4J
@parent ref:msg:01JH0Q6X9R8S7T6U5V4W3X2Y1Z
@deps ref:msg:01JH0Q6W8P7...
```

### 4. Validation & Integrity

* Anti-hallucination rule: `#rule no_new_facts=true` (intents can't contain facts)
* Content hashing: `@hash ref:hash:sha256:...` (immutable audit trail)
* Evidence tracking: `#evid claim="..." src=ref:... conf=0.85`

### 5. Economic Features (v1.1)

* **Budget enforcement**: `@budget 0.50USD` limits spending per task
* **Cost tracking**: `#cost val=0.02 cur=USD model=gpt-4o` reports actual costs
* **Quota management**: `#quota type=tokens total=100000 used=5000` tracks resource usage
* **Bidding**: agents propose resource needs before execution

---

## Use Cases

* **Multi-agent systems**: agents exchanging context/results
* **LLM pipelines**: research → analysis → writing
* **Agent logging/debugging**: compact audit trails
* **Human-in-the-loop**: review agent reasoning before execution
* **Agentic APIs**: structured requests/responses

Commercial use is permitted under Apache 2.0 (see [LICENSE](LICENSE)).

---

## Getting Started

### 1. Read the Spec

Start with [SPEC.md](SPEC.md) for the complete v1.1 specification.

### 2. Explore Examples

See [examples/](examples/) for:
* Basic request/response
* Threaded multi-agent conversations
* Evidence-based reporting
* Complex workflows

### 3. Implement or Integrate

**Reference implementations** (coming soon):
* Python parser/renderer
* TypeScript library
* Rust validator

**Integration**: PAIRL works as payload in any system (see §13.3 in SPEC.md)

---

## Project Status

**Current version**: 1.1 (February 2026)

* Core spec stabilized (v1.0)
* Economic features added (v1.1)
* Python validator available (tools/validator.py)
* Reference implementations in progress
* Community feedback welcome

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:

* How to propose spec changes
* Adding new intent types
* Reference implementation guidelines
* Reporting issues

---

## License

PAIRL specification and reference implementations are licensed under the **Apache License 2.0**.

This permissive license:
* Allows commercial use
* Includes explicit patent grant protection
* Requires attribution and license notice preservation

See [LICENSE](LICENSE) for full details.

---

## Links

* [Full Specification](SPEC.md)
* [Examples](examples/)
* [Contributing](CONTRIBUTING.md)
* [Changelog](CHANGELOG.md)

---

**PAIRL**: compact, reliable, interoperable agent communication.
