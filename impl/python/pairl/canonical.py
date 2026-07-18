"""Canonicalization and hashing (SPEC §9).

Columnar blocks are expanded to `#type key=value` records before
canonicalization (§9.4a), so a message hashes identically in either form.
"""

from __future__ import annotations

import hashlib

from .core import Message, Record

# Canonical header order (§9.1). Unknown headers are appended, sorted.
_HEADER_ORDER = ["v", "id", "mid", "sid", "ts", "p", "parent", "root", "deps", "budget", "limit"]
_ATOM_OK = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:._/@+-")


def _needs_quote(v: str) -> bool:
    return v == "" or any(c not in _ATOM_OK for c in v)


def _fmt_value(v: str) -> str:
    if _needs_quote(v):
        return '"' + v.replace('"', '\\"') + '"'
    return v


def serialize_record(r: Record) -> str:
    if r.kind == "marker":
        if r.parent is not None:  # verbose #msg
            return f"#msg {r.name} r={r.role} parent={r.parent}"
        return f"#{r.name}"

    if r.kind == "intent":
        params = ",".join(f"{k}={_fmt_value(v)}" for k, v in r.kv.items())
        head = f"{r.name}{{{params}}}" if r.kv or True else r.name
    elif r.kind == "s":
        head = f"#s {r.arg}" if r.arg else "#s"
    else:
        pairs = " ".join(f"{k}={_fmt_value(v)}" for k, v in r.kv.items())
        head = f"#{r.name} {pairs}".rstrip()

    trail = ""
    if r.m:
        trail += f" @m={r.m}"
    if r.rid:
        trail += f" @rid={r.rid}"
    return head + trail


def canonicalize(msg: Message, *, for_hash: bool = True) -> str:
    """Produce the canonical text. With for_hash, @hash is omitted (§9.6)."""
    lines: list[str] = []
    keys = list(msg.headers.keys())
    ordered = [k for k in _HEADER_ORDER if k in msg.headers]
    ordered += sorted(k for k in keys if k not in _HEADER_ORDER and k != "hash")
    if not for_hash and "hash" in msg.headers:
        ordered.append("hash")
    for k in ordered:
        lines.append(f"@{k} {msg.headers[k]}")

    lines.append("")  # blank line separating header block from body

    # Records already include columnar rows expanded into Record objects (§9.4a),
    # so iterating msg.records yields the canonical, expanded body.
    for r in msg.records:
        lines.append(serialize_record(r))

    return "\n".join(lines) + "\n"


def compute_hash(msg: Message) -> str:
    canon = canonicalize(msg, for_hash=True)
    digest = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    return digest


def hash_ref(msg: Message) -> str:
    return f"ref:hash:sha256:{compute_hash(msg)}"
