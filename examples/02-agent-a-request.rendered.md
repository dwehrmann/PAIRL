# Human Rendering: 02-agent-a-request.pairl

**This shows how a PAIRL renderer would convert the message to natural language for human consumption.**

---

## Original PAIRL Message

```
@v 1
@mid ref:msg:01JH0Q7A8B9C2D3E4F5G6H7I8J9K
@ts 2026-01-31T16:25:30.456+01:00
@root ref:msg:01JH0Q6Z7F8K4Q2S1R6E2E9A3B
@parent ref:msg:01JH0Q6Z7F8K4Q2S1R6E2E9A3B
@budget 0.50USD

bid{t=research,s=f,l=2,m=+,a=i} @rid=a1
#fact topic=ai_trends_2026 @rid=f1
#fact sources_count=5 @rid=f2
#fact estimated_tokens=15000 @rid=f3
#cost val=0.35 cur=USD note="estimated: 5 sources + summary" @rid=c1
#quota type=tokens total=15000 @rid=q1
#rule require_src_for_claims=true @rid=x1
```

---

## Rendered for Human

**From:** Research Agent (01JH0Q7A8B9C2D3E4F5G6H7I8J9K)
**Date:** January 31, 2026 at 4:25 PM CET
**In reply to:** [Original request](ref:msg:01JH0Q6Z7F8K4Q2S1R6E2E9A3B)
**Thread:** [Root message](ref:msg:01JH0Q6Z7F8K4Q2S1R6E2E9A3B)
**Budget available:** $0.50 USD

---

### Research Proposal

I propose to conduct research on **AI trends in 2026** with the following scope:

**Project details:**
- **Topic:** ai_trends_2026
- **Number of sources:** 5
- **Estimated token usage:** 15,000 tokens

**Cost estimate:**
- **Projected cost:** $0.35 USD
- **Breakdown:** 5 sources + summary generation
- **Budget remaining:** $0.15 USD (30% buffer)

**Quality assurance:**
- All claims will be backed by source citations (validation rule enforced)

**Awaiting your approval to proceed.**

---

## Rendering Notes

**Style signals used:**
- `s=f` (formal) → Professional proposal format
- `l=2` (normal length) → Standard detail level
- `m=+` (positive) → Constructive, solution-oriented
- `a=i` (internal audience) → Direct, technical language

**Economic features:**
- Budget header shown prominently
- Cost estimate displayed with breakdown
- Remaining budget calculated and highlighted
- Token quota mentioned for transparency

**Facts preserved:**
- All numerical values rendered exactly
- Source count and token estimates shown clearly
- Validation rule mentioned as quality assurance
