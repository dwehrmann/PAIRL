---
title: "Anlage 4: Spezifikationsauszug — PAIRL v1.2"
subtitle: "Formale Grammatik, Kanaltrennung und Validierungsregeln"
date: "März 2026"
---

# Auszug aus der PAIRL v1.2 Spezifikation

Die vollständige Spezifikation umfasst 15 Abschnitte und 4 Appendizes. Die folgenden Auszüge dokumentieren die formalen Kernelemente, die die Forschungsarbeit des Vorhabens betreffen.

## 1. Zwei-Kanal-Architektur (Spec §0.1)

PAIRL trennt jede Nachricht strukturell in zwei Kanäle:

**Lossy Intent Channel** — Parametrisierte Kurzformen für pragmatische Information:

```
req{t=analysis,s=f,l=2,m=+,a=c}
```

Parameter: `t` (Thema), `s` (Stil: formal/casual/terse), `l` (Länge: 0–3), `m` (Stimmung: +/-/!/0), `a` (Zielgruppe: intern/client/public)

**Lossless Fact Channel** — Typisierte Records für faktische Inhalte:

```
#fact deadline=2026-02-05
#ref  input=ref:doc:sha256:9c1a0f2b...
#evid claim="Q4 revenue exceeded projections" src=ref:msg:01JH...#f5 conf=0.90
#cost val=0.02 cur=USD model=gpt-4o
```

**Regel**: Alles, was später korrekt sein muss (Namen, Zahlen, IDs, Daten, URLs, Quellen, Kosten), gehört in den Lossless-Kanal.

## 2. Formale Grammatik (Spec §8.3)

Die folgende Grammatik definiert die minimale Syntax, die konforme Parser akzeptieren müssen:

```
message         := header-block LF body
header-block    := header-line *(LF header-line)
body            := *(record-line LF) [record-line]
header-line     := "@" hkey SP hval
record-line     := intent-record / hash-record

intent-record   := intent-name ["{" kvpairs "}"] [SP rid]
intent-name     := core-intent / custom-intent
core-intent     := 2*4(LOWER / DIGIT)
custom-intent   := ident "." ident *("." ident)

hash-record     := "#" ident SP kvpairs [SP rid]
rid             := "@rid=" 1*8(ALNUM)
kvpairs         := kvpair *("," kvpair) / kvpair *(SP kvpair)
kvpair          := key "=" value
key             := LOWER *(LOWER / DIGIT / "_")
value           := atom / quoted
quoted          := DQUOTE *(%x20-21 / %x23-5B / %x5D-10FFFF / '\"') DQUOTE
atom            := 1*(ALNUM / ":" / "." / "_" / "/" / "@" / "+" / "-")

ref             := short-ref / long-ref
short-ref       := "ref:" ns ":" ridpart ["#" ridfrag]
long-ref        := "ref:" ns ":" rtype ":" ridpart ["#" ridfrag]
```

## 3. Validierungsregeln (Spec §11)

PAIRL definiert 10 Validierungsregeln in zwei Modi (loose: Warnungen, strict: harte Fehler):

| Regel | Name | Beschreibung |
|---|---|---|
| **V1** | No-New-Facts | Intent-Kanal darf keine neuen Fakten einführen. Heuristische Prüfung auf URLs, Hashes, numerische Werte im Lossy-Kanal. |
| **V2** | Evidence Completeness | Jeder `#evid`-Record muss `claim`, `src` und `conf` enthalten. |
| **V3** | Ref Format | Referenzen müssen dem Format `ref:<ns>:<id>` oder `ref:<ns>:<type>:<id>` entsprechen. |
| **V4** | Thread Integrity | Referenzierte Eltern-Nachrichten müssen auflösbar sein (optional strict). |
| **V5** | Canonicalization Safety | Bei vorhandenem `@hash`: Neuberechnung und Vergleich, Abweichung ist Fehler. |
| **V6** | RID Uniqueness | Alle `@rid`-Werte innerhalb einer Nachricht müssen eindeutig sein. |
| **V7** | Circular Dependency | Zyklische Abhängigkeiten in `@deps`/`@parent` werden erkannt. |
| **V8** | Budget Compliance | Agenten müssen projizierte Kosten gegen Budget prüfen und bei Überschreitung ablehnen oder bieten. |
| **V9** | Tool Chain Integrity | `#ret`-Records müssen auf gültige `#call`-RIDs verweisen; Pflichtfelder werden geprüft. |
| **V10** | State Token Validity | `#s`-Records müssen einen Phasen-Wert enthalten; nur der letzte ist semantisch relevant. |

**V1 (Anti-Halluzination)** ist die zentrale Forschungsfrage: Die Regel erzwingt strukturell, dass Fakten ausschließlich im Lossless-Kanal kodiert werden. Die heuristische Erkennung von Fakten-Leakage in den Intent-Kanal ist ein offenes Problem (siehe Risikoanalyse im Antrag).

## 4. Nachrichtenbeispiel — Vollständige PAIRL-Nachricht

```
@v 1
@mid ref:msg:01JH0Q6Z7F8K4Q2S1R6E2E9A3B
@ts 2026-01-31T16:20:01.123+01:00
@root ref:msg:01JH0Q6YF1Z3QK9P8M7N6L5K4J
@parent ref:msg:01JH0Q6X9R8S7T6U5V4W3X2Y1Z
@budget 0.10USD
@hash ref:hash:sha256:9c1a0f2b3e4d5c6f7a8b9c0d1e2f3a4b

req{t=analysis,s=f,l=2,m=+,a=c} @rid=a1
#fact ask=market_analysis @rid=f1
#fact format=report @rid=f2
#fact deadline=2026-02-05 @rid=f3
#ref input=ref:doc:sha256:9c1a0f2b3e4d5c6f7a8b9c0d1e2f3a4b @rid=r1
#evid claim="Q4 revenue exceeded projections"
     src=ref:msg:01JH0Q6X9R8S7T6U5V4W3X2Y1Z#f5 conf=0.90 @rid=e1
#quota type=tokens total=100000 used=5000 rem=95000 @rid=q1
#cost val=0.02 cur=USD model=gpt-4o @rid=c1
#rule no_new_facts=true @rid=x1
```

Diese Nachricht kodiert: eine formale Anfrage für eine Marktanalyse (Intent), drei Fakten (Aufgabe, Format, Deadline), eine Quellenreferenz, einen Evidenz-Claim mit Konfidenz, Ressourcen-Tracking und eine Anti-Halluzinations-Regel — in 12 Zeilen statt typischerweise 200–400 Wörtern natürlicher Sprache.

## 5. Kanonisierung (Spec §9)

Für deterministische Hashes und Diffs definiert PAIRL eine strikte Kanonisierungsordnung:

**Header-Reihenfolge**: `@v` → `@mid` → `@ts` → `@root` → `@parent` → `@deps` → `@budget` → `@limit` → `@hash`

**Intent-Parameter-Reihenfolge**: `t,s,l,m,a,u,fmt` (kanonische Key-Order)

**Hash-Berechnung**: SHA-256 über kanonisierte UTF-8-Bytes ohne `@hash`-Header (nicht-zirkulär).

Diese Kanonisierung ermöglicht Content-adressierbare Speicherung und unveränderliche Audit-Trails — eine Anforderung, die bei keinem bestehenden NL-Kompressionsverfahren adressiert wird.
