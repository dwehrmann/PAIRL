# PAIRL Examples

This directory contains example PAIRL messages demonstrating various features and use cases.

---

## Example Files

Each example includes:
- **`.pairl`** file — the raw PAIRL message
- **`.rendered.md`** file — human-readable rendering (see §10 in SPEC.md)

1. **[01-basic-request.pairl](01-basic-request.pairl)** | [Rendered](01-basic-request.rendered.md)
   - Simple request message
   - Shows minimal required headers
   - Basic fact and reference records

2. **[02-agent-a-request.pairl](02-agent-a-request.pairl)** | [Rendered](02-agent-a-request.rendered.md)
   - Agent initiates research task
   - Includes budget constraints (v1.1)
   - Shows bid intent for resource proposal

3. **[03-agent-b-response.pairl](03-agent-b-response.pairl)** | [Rendered](03-agent-b-response.rendered.md)
   - Agent responds to request
   - Shows evidence-based reporting
   - Includes cost and quota tracking (v1.1)

4. **[04-threaded-summary.pairl](04-threaded-summary.pairl)** | [Rendered](04-threaded-summary.rendered.md)
   - Message threading with @parent
   - Summarizes previous conversation
   - References specific records from parent messages

5. **[05-complex-report.pairl](05-complex-report.pairl)** | [Rendered](05-complex-report.rendered.md)
   - Multi-record message
   - Evidence attribution with confidence scores
   - Economic features (budget, cost, quota)
   - Demonstrates validation rules

---

## Understanding PAIRL Rendering

**PAIRL is machine-to-machine format. Humans see rendered versions.**

Each example includes a `.rendered.md` file showing how a PAIRL renderer would convert the compact message into natural language for human consumption.

**Key concept:**
```
Agent A → [PAIRL message] → Agent B
                ↓
         [PAIRL renderer]
                ↓
             Human
```

**What renderers do:**
- Convert compact intents into natural prose
- Use style signals (`s`, `l`, `m`, `a`, `fmt`) to control tone/format
- Present facts and evidence in readable format
- Add context and formatting for clarity
- **Never** add facts not in the original message

See [SPEC.md §10](../SPEC.md) for full rendering guidelines.

---

## Reading PAIRL Messages

### Message Structure

Every PAIRL message has:

1. **Header block** (starts with `@`)
   - Required: `@v`, `@mid`, `@ts`
   - Optional: `@root`, `@parent`, `@deps`, `@budget`, `@limit`, `@hash`

2. **Empty line** (separator)

3. **Body** (records)
   - Lossy intents: `req{...}`, `sum{...}`, etc.
   - Lossless facts: `#fact`, `#ref`, `#evid`, `#rule`
   - Economic data: `#cost`, `#quota`

### Intent Parameters

Common parameters in `intent{...}`:
- `t` — topic/target
- `s` — style (f=formal, c=casual, t=trocken, p=poetisch, e=erhaben)
- `l` — length (0=ultra-short, 1=short, 2=normal, 3=longer)
- `m` — mood (+positive, -negative, !urgent, 0=neutral)
- `a` — audience (i=internal, c=client, p=public)
- `u` — uncertainty (lo, md, hi)
- `fmt` — format (par=paragraphs, bul=bullets, num=numbered)

---

## Thread Flow Example

The examples form a coherent conversation:

```
01-basic-request.pairl
  ↓ (user initiates task)
02-agent-a-request.pairl
  ↓ (agent proposes approach with budget)
03-agent-b-response.pairl
  ↓ (agent delivers results with evidence)
04-threaded-summary.pairl
  ↓ (summary of conversation)
05-complex-report.pairl
  (comprehensive report with all features)
```

---

## Using These Examples

### For Learning

1. Start with `01-basic-request.pairl` (simplest)
2. Progress through `02`, `03`, `04` to see threading
3. Study `05` for full feature set

### For Testing

Reference implementations should:
- Parse all examples without errors
- Validate against rules V1-V8
- Correctly canonicalize for hashing
- Extract facts, refs, evidence accurately

### For Templates

Copy and modify these examples for your own use cases:
- Replace `@mid` with your own ULIDs
- Update `@ts` timestamps
- Modify `#fact` and `#ref` values
- Adjust intent parameters to match your style

---

## Validation

All examples should pass:

```bash
# Using reference validator
python ../tools/validator.py 01-basic-request.pairl

# Expected output:
# ✓ Headers valid
# ✓ Records valid
# ✓ Budget compliance (if applicable)
# ✓ No validation errors
```

---

## Version Notes

- Examples `01-04` are **v1.0 compatible** (no economic features)
- Example `05` uses **v1.1 features** (@budget, #cost, #quota)
- v1.0 parsers can read all examples (may ignore v1.1 fields)

---

For detailed specification, see [../SPEC.md](../SPEC.md).
