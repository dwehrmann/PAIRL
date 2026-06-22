# Human Rendering: 07-turn-attribution.pairl

**This shows how a PAIRL renderer would convert the message to natural language for human consumption.**

This example demonstrates **v1.3 in-body turn attribution**: a whole multi-turn
conversation compressed into a single body, with compact turn markers (`#u1`, `#a2`, …)
recording *who said each line*. Because the markers are assigned by the encoder/gateway,
the speaker of every record is unambiguous — the renderer never has to guess.

---

## Original PAIRL Message

```
@v 1
@id m1
@sid ref:sess:01JH0Q8A1B2C3D4E5F6G7H8I9J
@ts 2026-06-08T10:15:00.000+02:00

#u1
req{t=db_migration,s=f,l=2,m=+,a=i} @rid=a1
#fact current_version=pg12 @rid=f1
#fact target_version=pg16 @rid=f2
#a2
pln{t=migration_strategy,s=f,l=2,m=+} @rid=a3
wrn{t=compatibility,s=f,l=1,m=!} @rid=a4
#fact tool=aws_dms @rid=f3
#fact strategy=blue_green @rid=f4
#fact risk=postgis_compatibility @rid=f5
#u3
qst{t=audit_log,s=f,l=1,m=0} @rid=a5
#a4
ack{t=data_preservation,s=f,l=1,m=+} @rid=a6
cnt{t=triggers,s=f,l=1,m=!} @rid=a7
#fact triggers_require_manual_recreation=true @rid=f6
#evid claim="DMS migrates data but not event triggers" src=ref:doc:aws:dms conf=0.95 @rid=e1
```

---

## Rendered for Human

**Turn 1 — User**
> We need to migrate our database, from PostgreSQL 12 to PostgreSQL 16. Can you put together a plan?

**Turn 2 — Assistant**
> Here's the plan: I'd use AWS DMS with a blue-green deployment. One risk to flag — PostGIS compatibility between the versions.

**Turn 3 — User**
> Sounds good. Will the audit log table survive the migration?

**Turn 4 — Assistant**
> Yes — your data is preserved. However, event triggers need to be recreated manually: DMS migrates data but not event triggers.

---

## Rendering Notes

**Turn attribution (v1.3):**
- `#u1`, `#u3` → spoken by the **user**; `#a2`, `#a4` → spoken by the **assistant**.
- Every record under a marker inherits that turn's speaker (section grouping) — e.g. `#fact tool=aws_dms` sits under `#a2`, so it is unambiguously the **assistant's** proposal, and `qst{t=audit_log}` under `#u3` is the **user's** question.
- No record needs an explicit `@m=` tag here; grouping carries the attribution with almost no overhead.

**Why it matters:**
- Without turn markers, a renderer would have to *guess* the speaker from the intent type and order — and would sometimes mis-assign a fact to the wrong person (e.g. reconstructing the assistant as stating something the user said). The markers make that impossible.

**Facts preserved (lossless channel):**
- `pg12` → PostgreSQL 12, `pg16` → PostgreSQL 16 (rendered exactly).
- The `#evid` claim about DMS and event triggers is carried with its source and confidence.

**Style signals used:**
- `s=f` (formal) → professional tone.
- `m=!` on `wrn`/`cnt` → flags the compatibility risk and the trigger caveat as important.
