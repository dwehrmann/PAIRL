# Human Rendering: 04-threaded-summary.pairl

**This shows how a PAIRL renderer would convert the message to natural language for human consumption.**

---

## Original PAIRL Message

```
@v 1
@id m4
@ts 2026-01-31T16:40:00.123+01:00
@p m3
@deps m2

sum{t=conversation,s=c,l=1,m=0,a=i,fmt=bul} @rid=a1
#fact thread_messages=3 @rid=f1
#fact total_cost_usd=0.28 @rid=f2
#fact budget_remaining_usd=0.22 @rid=f3
#ref initial_request=@m1#a1 @rid=r1
#ref research_bid=@m2#a1 @rid=r2
#ref research_results=@m3#r1 @rid=r3
#quota type=tokens total=15000 used=12500 @rid=q1
```

---

## Rendered for Human

**From:** Summary Agent (01JH0Q7C0D1E2F3G4H5I6J7K8L9M)
**Date:** January 31, 2026 at 4:40 PM CET
**In reply to:** [Research results](@m3)
**Thread:** [Root message](@m1)

---

### Thread Summary

Here's a quick overview of this conversation:

**Thread metrics:**
- Messages exchanged: 3
- Total cost: $0.28 USD
- Budget remaining: $0.22 USD (44% left)
- Token usage: 12,500 / 15,000 (83%)

**Conversation flow:**

1. **Initial request** → [View](@m1#a1)
   - User requested AI trends research

2. **Research proposal** → [View](@m2#a1)
   - Agent proposed $0.35 approach with 5 sources

3. **Research results** → [View](@m3#r1)
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
- Thread context maintained through @p (parent); @root omitted because it is derivable via the @p chain
- Dependencies (@deps) shown implicitly in flow diagram
