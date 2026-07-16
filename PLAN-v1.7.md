# PLAN v1.7 — PAIRL as Response Format (A2A-Native Output)

Status: draft plan, pre-spec. Nothing here is normative until it lands in SPEC.md
with measured evidence, following the v1.6 pattern (pre-registered pairl-bench
stages gating every normative claim).

---

## 1. Motivation

Through v1.6, PAIRL compresses the **input** side of an LLM call: conversation
history is encoded once and delivered compactly. Production metering (gateway,
2026-07) shows the ceiling of that lever: on thinking-class models the
**output** side dominates total cost — output tokens bill at ~5× the input
rate, thinking is billed as output, and a request whose input side saved ~70%
still spent >90% of its total cost on output. Input-side compression cannot
touch that.

The output side has an untapped asymmetry: when the consumer of a response is
**another agent**, prose is overhead. PAIRL was designed as an agent-to-agent
format ("render to natural language only when needed", §preamble) — v1.7
extends that principle from *messages agents exchange* to *the model response
itself*: the model answers in PAIRL, and only human endpoints ever pay for
rendering.

## 2. Two consumer profiles

### Profile A — `a2a` (primary): agent consumes the response

The requester declares that the caller is an agent with PAIRL competence
(spec/legend already in its context). The responder emits a PAIRL body **as**
the answer. No decode step exists; the savings are the full prose→PAIRL delta.

Compounding effect with §12b (maintained sessions): the PAIRL response of call
N is already in canonical form and can be appended to the maintained body for
call N+1 **without re-encoding** — the answer side of a pipeline never pays an
encoder again. A gateway operating both sides gets the reduction twice per
hop: once as output of call N, once as input of call N+1.

### Profile B — `render` (human endpoint): decode to prose

Already the spec's stated philosophy (examples ship as `.pairl` +
`.rendered.md` pairs). A decode pass (cheap model, or a future PAIRL-native
model — §6) expands the PAIRL answer to prose for the human reader.

Open fidelity question, to be **measured, not assumed** (see §5): the response
is model-authored (generative), so the v1.6 extractive zero-hallucination
guarantee does not apply to it, and the render pass adds a second generative
step. Whether the two-step path (expensive model → PAIRL → cheap render)
loses measurable quality against direct prose from the expensive model is an
empirical question — and answering exactly this kind of question is what the
lossless channel and the validator exist for.

## 3. Spec surface (candidate additions)

1. **Response-format negotiation.** A way for a request to declare "answer in
   PAIRL": candidate shapes — a header field on the requesting message, or a
   `#fmt` record in the request body. Must be ignorable by non-PAIRL
   responders (graceful degradation to prose).
2. **Response-body profile.** A `#rpt`-rooted body form for answers:
   which records are REQUIRED (lossless channel for every citable value —
   names, numbers, IDs, dates, URLs, sources — per §0.1's rule of thumb),
   what the lossy channel may carry, how the answer threads to the request
   (`@p`).
3. **Validation rules for authored bodies.** V-rules that a gateway can check
   mechanically on a model-authored response: lossless-channel discipline
   (citable values MUST appear in `#fact`/`#ref`), RID/marker well-formedness,
   and a fallback contract — an invalid PAIRL response is re-requested as
   prose or passed through marked as unvalidated, never silently trusted.
4. **Render contract (Profile B).** What a renderer MUST preserve (all
   lossless-channel values verbatim) and MAY do (surface prose freely). This
   is where the render-fidelity benchmark (§5) gets its pass/fail line.

## 4. Gateway integration sketch (informative, not spec)

- Opt-in per request (e.g. `X-PAIRL-Output: a2a | render`).
- Gateway injects the answer-in-PAIRL instruction + response legend, validates
  the returned body (V-rules above), falls back to prose on validation failure.
- `render` profile: gateway runs the decode pass before returning; economics
  gate — decode-model output cost must stay well under the origin-model tokens
  saved (favorable whenever origin output rate ≫ render output rate, e.g.
  50:1 for frontier thinking models vs. flash-class renderers).
- Honest baseline: measured savings must be reported **against a
  brevity-instructed prose baseline**, not against unconstrained prose — a
  "be concise" instruction is free and captures part of the same reduction.

## 5. Measurement gates (pairl-bench, pre-registered before spec text)

1. **Authored-response fidelity (gates Profile A).** Task suites answered in
   prose vs. PAIRL; score citable-value accuracy of a downstream agent
   consuming each. Pass: PAIRL parity with prose on value accuracy.
2. **Render fidelity (gates Profile B).** Frontier-model prose (direct) vs.
   frontier-model PAIRL → cheap-model render. Score value accuracy AND prose
   quality. This is the open question behind the "expensive model drafts,
   cheap model phrases" concern — resolved by data, either direction.
3. **Economics.** Real token counts (PAIRL tokenizes dense, ~2.8 chars/token —
   character savings overstate token savings), against the brevity baseline,
   on both profiles. Thinking tokens are out of scope by construction — no
   output format reaches them; report them separately so savings claims stay
   honest relative to total cost.

## 6. Long-term option: PAIRL-native model

A model fine-tuned to speak PAIRL natively changes both profiles: as
**responder**, it removes the instruction overhead and the validation failure
rate; as **renderer** (Profile B), a small model trained on the render
contract is the credible answer to the fidelity concern — translation is then
a trained competence, not an improvised paraphrase. The v1.7 spec should not
depend on it, but its record shapes should be chosen so that such a model's
training data can be generated mechanically from existing `.pairl` +
`.rendered.md` pairs.

## 7. Non-goals for v1.7

- No change to the input-side encoding contract (§12a/§12b stay as-is).
- No thinking-token claims: thinking is billed as output and unaffected by
  response format; v1.7 must not market savings against it.
- No normative gateway behavior in SPEC.md beyond the validation/fallback
  contract — deployment mechanics stay in the gateway.
