"""Deterministic PAIRL -> human-readable renderer.

This is a faithful, template-based rendering (no LLM): it never invents facts
and reproduces all #fact/#evid values verbatim (SPEC §12). For fluent natural
language, feed the message to an LLM renderer instead.
"""

from __future__ import annotations

from .core import Message, Record

_INTENT_LABELS = {
    "req": "Request", "qst": "Question", "ack": "Acknowledgement", "pln": "Plan",
    "nxt": "Next action", "sum": "Summary", "upd": "Status update", "fin": "Done",
    "blk": "Blocked", "ctx": "Context", "fnd": "Findings", "evl": "Assessment",
    "cmp": "Comparison", "lst": "List", "def": "Clarification", "wrn": "Warning",
    "agr": "Agreement", "dis": "Disagreement", "alt": "Alternative", "emf": "Emphasis",
    "cnt": "Contrast", "rpt": "Report (unconfirmed)", "off": "Official", "inc": "Incident",
    "apx": "Apology", "thx": "Thanks", "grt": "Greeting", "cls": "Closing", "bid": "Cost proposal",
}
_ROLE = {"u": "User", "a": "Assistant", "s": "System"}


def render(msg: Message) -> str:
    out: list[str] = []
    mid = msg.msg_id or "(no id)"
    out.append(f"# PAIRL message {mid}")
    meta = []
    if msg.headers.get("ts"):
        meta.append(f"time {msg.headers['ts']}")
    if msg.headers.get("p"):
        meta.append(f"in reply to {msg.headers['p']}")
    if msg.headers.get("budget"):
        meta.append(f"budget {msg.headers['budget']}")
    if meta:
        out.append("_" + " · ".join(meta) + "_")
    out.append("")

    current_turn = None
    for r in msg.records:
        if r.kind == "marker":
            current_turn = r
            speaker = _ROLE.get(r.role or "", r.role or "?")
            out.append(f"## {speaker} ({r.name})")
            continue
        line = _render_record(r)
        if line:
            out.append(line)

    return "\n".join(out).rstrip() + "\n"


def _render_record(r: Record) -> str:
    if r.kind == "intent":
        label = _INTENT_LABELS.get(r.name or "", (r.name or "intent"))
        topic = r.kv.get("t")
        s = f"- **{label}**"
        if topic:
            s += f": {topic.replace('_', ' ')}"
        mood = r.kv.get("m")
        if mood == "!":
            s += " (urgent)"
        return s
    if r.kind == "fact":
        return "  - " + "; ".join(f"{k} = {v}" for k, v in r.kv.items())
    if r.kind == "evid":
        claim = r.kv.get("claim", "")
        src = r.kv.get("src", "?")
        conf = r.kv.get("conf", "?")
        try:
            conf = f"{float(conf) * 100:.0f}%"
        except ValueError:
            pass
        return f'  - Evidence: "{claim}" — source {src}, confidence {conf}'
    if r.kind == "ref":
        return "  - Reference: " + "; ".join(f"{k} → {v}" for k, v in r.kv.items())
    if r.kind == "rule":
        return "  - Rule: " + ", ".join(f"{k}={v}" for k, v in r.kv.items())
    if r.kind == "cost":
        val = r.kv.get("val", "?")
        cur = r.kv.get("cur", "")
        extra = f" ({r.kv['model']})" if r.kv.get("model") else ""
        return f"  - Cost: {val} {cur}{extra}".rstrip()
    if r.kind == "quota":
        t = r.kv.get("type", "?")
        used = r.kv.get("used")
        total = r.kv.get("total")
        rem = r.kv.get("rem")
        bits = [f"{t}"]
        if used and total:
            bits.append(f"used {used}/{total}")
        if rem:
            bits.append(f"{rem} remaining")
        return "  - Quota: " + ", ".join(bits)
    if r.kind == "call":
        return f"  - Tool call: {r.kv.get('tool', '?')}"
    if r.kind == "ret":
        return f"  - Tool result ({r.kv.get('status', '?')})"
    if r.kind == "think":
        return f"  - Reasoning: {r.kv.get('summary', '')}"
    if r.kind == "edit":
        return f"  - Edit: {r.kv.get('file', '?')} ({r.kv.get('changes', '?')} changes)"
    if r.kind == "s":
        return None
    return None
