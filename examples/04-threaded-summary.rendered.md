# Human Rendering: 04-threaded-summary.pairl

**This shows how a PAIRL renderer would convert the message to natural language for human consumption.**

---

## Original PAIRL Message

```
@v 1
@mid ref:msg:01JH0Q7C0D1E2F3G4H5I6J7K8L9M
@ts 2026-01-31T16:40:00.123+01:00
@root ref:msg:01JH0Q6Z7F8K4Q2S1R6E2E9A3B
@parent ref:msg:01JH0Q7B9C0D1E2F3G4H5I6J7K8L
@deps ref:msg:01JH0Q7A8B9C2D3E4F5G6H7I8J9K,ref:msg:01JH0Q6Z7F8K4Q2S1R6E2E9A3B

sum{t=conversation,s=c,l=1,m=0,a=i,fmt=bul} @rid=a1
#fact thread_messages=3 @rid=f1
#fact total_cost_usd=0.28 @rid=f2
#fact budget_remaining_usd=0.22 @rid=f3
#ref initial_request=ref:msg:01JH0Q6Z7F8K4Q2S1R6E2E9A3B#a1 @rid=r1
#ref research_bid=ref:msg:01JH0Q7A8B9C2D3E4F5G6H7I8J9K#a1 @rid=r2
#ref research_results=ref:msg:01JH0Q7B9C0D1E2F3G4H5I6J7K8L#r1 @rid=r3
#quota type=tokens total=15000 used=12500 @rid=q1
```

---

## Rendered for Human

**From:** Summary Agent (01JH0Q7C0D1E2F3G4H5I6J7K8L9M)
**Date:** January 31, 2026 at 4:40 PM CET
**In reply to:** [Research results](ref:msg:01JH0Q7B9C0D1E2F3G4H5I6J7K8L)
**Thread:** [Root message](ref:msg:01JH0Q6Z7F8K4Q2S1R6E2E9A3B)

---

### Thread Summary

Here's a quick overview of this conversation:

**Thread metrics:**
- Messages exchanged: 3
- Total cost: $0.28 USD
- Budget remaining: $0.22 USD (44% left)
- Token usage: 12,500 / 15,000 (83%)

**Conversation flow:**

1. **Initial request** → [View](ref:msg:01JH0Q6Z7F8K4Q2S1R6E2E9A3B#a1)
   - User requested AI trends research

2. **Research proposal** → [View](ref:msg:01JH0Q7A8B9C2D3E4F5G6H7I8J9K#a1)
   - Agent proposed $0.35 approach with 5 sources

3. **Research results** → [View](ref:msg:01JH0Q7B9C0D1E2F3G4H5I6J7K8L#r1)
   - Agent delivered findings for $0.28 (under budget)

**Status:** ✓ Complete, under budget

---

## Rendering Notes

**Style signals used:**
- `s=c` (casual) → Conversational, friendly tone
- `l=1` (short) → Brief, bullet-point format
- `m=0` (neutral) → Factual, no emotional framing
- `a=i` (internal) → Team-level summary
- `fmt=bul` (bullets) → Bulleted list format used

**Thread visualization:**
- Shows conversation flow with numbered steps
- Links to specific records within messages (using `#rid`)
- Highlights key metrics at top
- Status indicator based on budget compliance

**Facts preserved:**
- All numerical values rendered exactly
- Message count matches actual thread length
- Cost and budget calculations accurate
- Token usage preserved from parent message

**References:**
- Direct links to specific records in parent messages
- Thread context maintained through @root and @parent
- Dependencies (@deps) shown implicitly in flow diagram
