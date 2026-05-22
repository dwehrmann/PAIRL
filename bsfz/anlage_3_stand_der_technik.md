---
title: "Anlage 3: Stand der Technik — Vergleichsanalyse"
subtitle: "PAIRL — Protocol for Agent Intermediate Representation (Lite)"
date: "März 2026"
---

# Vergleich: PAIRL vs. bestehende Ansätze

## 1. Vergleichstabelle

| Kriterium | Stand der Technik | PAIRL |
|---|---|---|
| **Ansatz** | LLMLingua: statistische Token-Entfernung auf Basis von Perplexität. Selective Context: Entfernung von Sätzen mit niedriger Self-Information. JSON-RPC/gRPC: strukturierte API-Aufrufe mit festen Schemata. | Semantische Zerlegung in typisierte Intent- und Fakten-Records |
| **Kompressionstyp** | Token-Level (LLMLingua) bzw. Satz-Level (Selective Context); keine Kompression bei JSON-RPC | Semantisch-strukturell auf Nachrichtenebene |
| **Ausgabeformat** | Unstrukturierter Freitext (LLMLingua, Selective Context) bzw. festes JSON-Schema (RPC) | Typisiertes Nachrichtenprotokoll mit formaler Grammatik |
| **Semantische Struktur** | Nein bei Token-Kompression; nur vordefinierte Felder bei RPC | Ja — explizite Kategorien (#fact, #ref, #evid, #cost) |
| **Validierbarkeit** | Nicht maschinell validierbar (Token-Kompression); Schema-Validierung (RPC) | Formale Grammatik + 10 Validierungsregeln (V1–V10) |
| **Anti-Halluzination** | Keine Maßnahme (Token-Kompression); nicht anwendbar (RPC) | Strukturelle Kanaltrennung: Fakten nur im Lossless-Kanal; maschinell prüfbar (V1) |
| **Pragmatische Information** | Geht bei Kompression verloren; nicht vorgesehen bei RPC | Erhalten im Lossy-Kanal (Stil, Stimmung, Zielgruppe, Länge) |
| **Modellabhängigkeit** | Erfordert spezifisches LLM zur Perplexitätsberechnung | Modellunabhängig (Protokollspezifikation) |
| **Roundtrip-Fähigkeit** | Nein — Originaltext nicht rekonstruierbar (Token-Kompression) | Ja — PAIRL→NL Decoding mit Intent-gesteuerter Rekonstruktion |
| **Multi-Agent-Eignung** | Nicht konzipiert für Agent-Chains (Token-Kompression); Punkt-zu-Punkt (RPC) | Threading (DAG), Budget-Tracking, Referenzierung |
| **Kompressionsrate** | 40–70% Token-Reduktion (Token-Kompression); nicht anwendbar (RPC) | 70–90% Token-Reduktion (NL→PAIRL) |

## 2. Detaillierte Abgrenzung

### 2.1 Gegenüber statistischer Token-Kompression (LLMLingua, Selective Context)

LLMLingua (Jiang et al., 2023, Microsoft Research) und Selective Context (Li et al., 2023) sind die derzeit meistzitierten Ansätze zur Prompt-Kompression. Beide entfernen Tokens bzw. Sätze basierend auf statistischen Kennzahlen (Perplexität, Self-Information), ohne die semantische Struktur der Nachricht zu analysieren.

**Fundamentaler Unterschied**: Die Ausgabe dieser Verfahren ist weiterhin unstrukturierter Freitext. Es gibt keine Möglichkeit, maschinell zu prüfen, ob Fakten korrekt erhalten wurden, ob Halluzinationen eingeführt wurden oder ob pragmatische Information (Stil, Zielgruppe) bewahrt wurde. PAIRL erzeugt stattdessen ein typisiertes Zwischenformat, in dem jede Information einer expliziten Kategorie zugeordnet ist und gegen formale Regeln validiert werden kann.

Zusätzlich sind diese Verfahren modellspezifisch — sie benötigen ein LLM zur Berechnung der Perplexitätswerte. PAIRL als Protokollspezifikation ist modellunabhängig.

### 2.2 Gegenüber strukturierten API-Protokollen (JSON-RPC, gRPC, OpenAPI)

Klassische API-Protokolle bieten strukturierte Kommunikation mit Schema-Validierung. Sie sind jedoch für deterministische Maschine-zu-Maschine-Kommunikation konzipiert, nicht für die probabilistische, semantisch reiche Kommunikation zwischen KI-Agenten.

**Fundamentaler Unterschied**: JSON-RPC und gRPC verlieren jegliche pragmatische Information — es gibt keine Möglichkeit, Stil, Stimmung oder Zielgruppe zu kodieren. Für die Rekonstruktion natürlichsprachlicher Ausgaben an menschliche Endpunkte fehlen diese Informationen. PAIRL kombiniert strukturierte Daten (Lossless-Kanal) mit parametrisierten pragmatischen Hinweisen (Lossy-Kanal) — eine Kombination, die in keinem bestehenden Protokoll existiert.

### 2.3 Gegenüber Multi-Agent-Frameworks (AutoGPT, CrewAI, LangGraph)

Bestehende Multi-Agent-Frameworks wie AutoGPT (Richards, 2023), CrewAI (Moura, 2024) und LangGraph (LangChain, 2024) verwenden natürliche Sprache für die Inter-Agent-Kommunikation. Sie definieren kein Nachrichtenformat — Agenten tauschen Freitext-Strings aus.

**Fundamentaler Unterschied**: In mehrstufigen Agent-Chains akkumuliert sich redundanter Kontext, da jeder Agent die vollständige natürlichsprachliche Nachricht seines Vorgängers im Kontext hält. PAIRL adressiert dieses Skalierungsproblem auf Protokollebene: Durch Referenzierung statt Kopie (Pointer-First-Prinzip, Content-adressierbare Hashes) und strukturierte Kompression wächst der Kontext nicht mehr linear mit der Hop-Anzahl.

## 3. Zusammenfassung

Kein bestehendes Verfahren kombiniert:

1. Semantische Strukturierung mit expliziten Kategorien
2. Erhalt pragmatischer Information (Stil, Stimmung, Zielgruppe)
3. Maschinelle Anti-Halluzinations-Validierung
4. Roundtrip-Fähigkeit (NL→Format→NL)
5. Multi-Agent-Eignung (Threading, Budgets, Referenzierung)

PAIRL ist nach Kenntnis des Antragstellers das erste Protokoll, das diese fünf Eigenschaften in einem Nachrichtenformat vereint.
