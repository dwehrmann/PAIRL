# Human Rendering: 01-basic-request.pairl

**This shows how a PAIRL renderer would convert the message to natural language for human consumption.**

---

## Original PAIRL Message

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

---

## Rendered for Human

**From:** Agent (01JH0Q6Z7F8K4Q2S1R6E2E9A3B)
**Date:** January 31, 2026 at 4:20 PM CET

---

### Request for Specifications

I'm requesting a specification document with the following requirements:

**Requirements:**
- **What I need:** spec_document
- **Format:** PDF or link
- **Deadline:** February 5, 2026

**Reference document:** [View document](ref:doc:sha256:9c1a0f2b3e4d5c6f7a8b9c0d1e2f3a4b)

---

## Rendering Notes

**Style signals used:**
- `s=f` (formal) → Professional tone
- `l=2` (normal length) → Standard detail level
- `m=+` (positive) → Constructive, friendly phrasing
- `a=c` (client audience) → External-facing language

**Facts preserved:**
- All `#fact` values rendered exactly as specified
- Deadline shown in human-readable format
- Reference link provided (actual resolution depends on ref resolver)
