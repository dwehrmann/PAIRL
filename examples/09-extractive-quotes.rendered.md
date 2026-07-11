# Human Rendering: 09-extractive-quotes.pairl

**This shows how a PAIRL renderer would convert the message to natural language for human consumption.**

A four-turn support conversation compressed into one body using the **v1.6 carriage forms** (SPEC §3.1): three turns carried as **extractive quotes** — every character inside `content="…"` is copied verbatim from the original turn, ` [...] ` marks omitted text — and one turn carried as an explicitly **marked condensate** (`mode=cond`), the only place encoder-authored paraphrase is allowed. Hard values additionally live in `#fact` records; intents (`wrn`, `fin`) appear as optional stance signals.

---

## Original PAIRL Message

```
@v 1
@id m6
@ts 2026-07-11T09:00:00.000+02:00

#u1
#req content="Our API latency spiked to 800ms P99 after the Redis upgrade. Before it was 120ms. [...] connection pool exhaustion starting at 14:32 UTC." @rid=q1
#fact p99_latency_after=800ms @rid=f1
#fact p99_latency_before=120ms @rid=f2
#fact issue_start="14:32 UTC" @rid=f3
#a2
#rpt content="Check maxclients in redis.conf — Redis 7.2 lowered the default from 10000 to 4096. Your pool size of 200 connections per pod across 12 pods = 2400, which fits, but if some connections are stuck in CLOSE_WAIT you could hit the limit." @rid=q2
wrn{t=connection_limit} @rid=a1
#fact redis_maxclients_default_7_2=4096 @rid=f4
#u3
#req content="maxclients was at 4096 and we had 3800 active connections. Bumped it to 8192 and latency is back to 115ms." @rid=q3
fin{t=fix_confirmed} @rid=a2
#fact active_connections=3800 @rid=f5
#fact fix="maxclients bumped to 8192, latency back to 115ms" @rid=f6
#a4
#rpt content="Closes the incident and recommends alerting when connected_clients exceeds 80% of maxclients, so the next approach to the limit is visible early." mode=cond @rid=q4
```

---

## Rendered Output

**User** reported that API latency spiked to **800ms P99** after the Redis upgrade (previously **120ms**), with connection pool exhaustion visible from **14:32 UTC**.

**Assistant** advised checking `maxclients` in redis.conf — Redis 7.2 lowered the default from 10000 to **4096** — and warned that a pool of 200 connections × 12 pods = 2400 fits, but connections stuck in CLOSE_WAIT could still hit the limit.

**User** confirmed the diagnosis: `maxclients` was at 4096 with **3800** active connections; raising it to **8192** brought latency back to **115ms**.

**Assistant** closed the incident and recommended alerting when `connected_clients` exceeds 80% of `maxclients`. *(This turn is a marked summary — `mode=cond` — not a quote.)*

---

## Key Points

* **Unmarked `#req`/`#rpt` records are quotations** — a reader can rely on their wording as evidence of what was said. The first three turns above quote the original conversation verbatim, with ` [...] ` standing for omitted text.
* **`mode=cond` is the only place paraphrase is allowed** — the fourth turn is an encoder-authored summary and is permanently recognizable as one.
* **Citable values live in `#fact`** regardless of carriage form (original surface form, quoted where atoms can't carry it: `#fact issue_start="14:32 UTC"`).
* **Turn markers attribute deterministically**: `#u1`/`#a2`/`#s3` are assigned by the encoder/gateway from structural metadata, never inferred by a model.
* **Why quotes instead of a summary?** Measured in the public [pairl-bench](https://github.com/dwehrmann/pairl-bench) STAGE-7 study: the extractive carrier reached coverage parity with LLM summarization at 60% token reduction — with material hallucination at roughly half the summarizer's rate, because content invention is structurally impossible when every content byte is source-copied.
