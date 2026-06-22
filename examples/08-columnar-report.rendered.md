# Human Rendering: 08-columnar-report.pairl

**This shows how a PAIRL renderer would convert the message to natural language for human consumption.**

This is the same report as [05-complex-report](05-complex-report.pairl), re-encoded with **v1.5 columnar record blocks** (and v1.4 short refs). The two messages are semantically identical and render the same — columnar is a transport-level encoding, expanded back to `key=value` records before canonicalization/hashing (SPEC §9.4a).

---

## Original PAIRL Message

```
@v 1
@id m5
@ts 2026-01-31T17:00:00.000+01:00
@p m4
@budget 0.50USD

rpt{t=final_report,s=f,l=3,m=+,a=c,u=lo,fmt=par}
#fact report_title="AI Trends 2026: Comprehensive Analysis"
#fact report_date=2026-01-31
#fact sections_count=5
#fact word_count=2500
#fact confidence_avg=0.83
#ref full_report=ref:doc:sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
#ref s1=ref:url:techcrunch:2025-12-15
#ref s2=ref:url:gartner:2026-01-10
#ref s3=ref:url:forrester:2026-01-20
#ref s4=ref:url:arxiv:2026-01-15
#ref s5=ref:url:mit-tech-review:2026-01-25
#evid[claim,src,conf]
"LLM costs decreased 60% in 2025" s1 0.85
"Multi-agent systems adoption increased 300%" s2 0.90
"PAIRL adoption growing in enterprise" s3 0.75
"Transformer alternatives showing promise" s4 0.70
"AI regulation frameworks converging globally" s5 0.88
#cost val=0.42 cur=USD model=gpt-4o note="research + analysis + report generation"
#quota[type,total,used,rem]
tokens 50000 38500 11500
api_calls 25 18 7
#rule no_new_facts=true
#rule require_src_for_claims=true
---
```

The `#evid[claim,src,conf]` block expands to five `#evid claim=… src=… conf=…` records; `#quota[type,total,used,rem]` expands to two `#quota` records — identical to example 05's body. `#fact`, `#ref`, and `#rule` stay in `key=value` form because their key is data (variable per line), not a fixed schema.

---

## Rendered for Human

**From:** Report Agent
**Date:** January 31, 2026 at 5:00 PM CET
**In reply to:** [Thread summary](@m4)
**Budget available:** $0.50 USD

---

# AI Trends 2026: Comprehensive Analysis

**Report Date:** January 31, 2026
**Sections:** 5 | **Word Count:** 2,500 | **Overall Confidence:** 83%

[Download full report](ref:doc:sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855)

## Key Findings

1. **Large language model costs decreased 60% in 2025.** — *TechCrunch, December 15, 2025 (confidence 85%)*
2. **Multi-agent systems adoption increased 300%.** — *Gartner, January 10, 2026 (confidence 90%)*
3. **AI regulation frameworks are converging globally.** — *MIT Technology Review, January 25, 2026 (confidence 88%)*
4. **PAIRL adoption is growing in enterprise.** — *Forrester, January 20, 2026 (confidence 75%)*
5. **Transformer alternatives are showing promise.** — *arXiv preprint, January 15, 2026 (confidence 70%)*

---

## Resource Utilization

- **Cost:** $0.42 USD of $0.50 USD budget (under by $0.08) — model GPT-4o
- **Tokens:** 38,500 / 50,000 used (77%), 11,500 remaining
- **API calls:** 18 / 25 used (72%), 7 remaining
- **Quality:** all claims sourced; no unsupported facts (validation enforced)

---

## Rendering Notes

**v1.5 columnar form:**
- `#evid[claim,src,conf]` declares the evidence schema once; each following row maps positionally — `"claim" src conf`. The first field is a quoted string (it contains spaces); `src` and `conf` are atoms.
- `#quota[type,total,used,rem]` does the same for the two quota rows.
- A renderer (or validator) expands each row to the equivalent `key=value` record, so all downstream behavior — fact preservation, evidence attribution, hashing — is unchanged from the verbose form.

**Why only these records:**
- `#evid` and `#quota` have a **fixed key schema** that repeats across rows → columnar removes the repeated keys.
- `#fact` and `#ref` keep `key=value`: their "key" (`report_title`, `s1`, …) is itself data, so there is no shared schema to factor out.
