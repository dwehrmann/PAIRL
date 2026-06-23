"""PAIRL v1.5 validation rules (V1–V12) operating on a parsed Message."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .core import COLUMNAR_FORBIDDEN, Message, split_fields

_REF = re.compile(r"^ref:[A-Za-z0-9_-]+:[^\s]+$")
_SLOC = re.compile(r"^@[A-Za-z0-9]{1,8}(?:#[A-Za-z0-9_-]{1,8})?$")
_BARE_DEP = re.compile(r"^[A-Za-z0-9]{1,8}(?:#[A-Za-z0-9_-]{1,8})?$")
_BUDGET = re.compile(r"^([0-9]+(?:\.[0-9]+)?)([A-Za-z]{1,16})$")
_NUMERIC_INTENT_KEYS = {"l", "m"}


def is_valid_ref(v: str) -> bool:
    if not v.startswith("ref:") or " " in v:
        return False
    main = v.split("#", 1)[0]
    return len(main.split(":")) >= 3 and bool(_REF.match(main))


def is_sloc_ref(v: str) -> bool:
    return bool(_SLOC.match(v))


@dataclass
class Result:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


def validate(msg: Message, strict: bool = False) -> Result:
    res = Result()
    res.errors.extend(msg.errors)

    # Required headers
    for h in ("v", "ts"):
        if h not in msg.headers:
            res.errors.append(f"missing required header: @{h}")
    if "id" not in msg.headers and "mid" not in msg.headers:
        res.errors.append("missing required header: @id (or legacy @mid)")

    _v1_no_new_facts(msg, res, strict)
    _v2_evidence(msg, res)
    _v3_refs(msg, res)
    _v6_rid_unique(msg, res)
    _v8_budget(msg, res)
    _v9_tool_chain(msg, res, strict)
    _v11_turn_markers(msg, res)
    _v12_columnar(msg, res)
    return res


def _has_rule(msg: Message, name: str) -> bool:
    return any(r.kind == "rule" and r.kv.get(name) == "true" for r in msg.records)


def _v1_no_new_facts(msg: Message, res: Result, strict: bool) -> None:
    enforce = strict and _has_rule(msg, "no_new_facts")
    for r in msg.records:
        if r.kind != "intent":
            continue
        for k, v in r.kv.items():
            if re.search(r"https?://", v):
                _emit(res, enforce, f"V1: intent param '{k}' has a URL (move to #ref): {v}")
            elif re.search(r"[a-fA-F0-9]{12,}", v):
                _emit(res, enforce, f"V1: intent param '{k}' looks like a hash (move to #ref): {v}")
            elif k not in _NUMERIC_INTENT_KEYS and re.search(r"\d", v):
                _emit(res, enforce, f"V1: intent param '{k}' has a number (consider #fact): {k}={v}")


def _v2_evidence(msg: Message, res: Result) -> None:
    for r in msg.records:
        if r.kind != "evid":
            continue
        missing = [k for k in ("claim", "src", "conf") if k not in r.kv]
        if missing:
            res.errors.append(f"V2: #evid missing {', '.join(missing)}: {r.raw}")
            continue
        try:
            c = float(r.kv["conf"])
            if not (0.0 <= c <= 1.0):
                res.errors.append(f"V2: #evid conf must be in [0,1]: {r.raw}")
        except ValueError:
            res.errors.append(f"V2: #evid conf is not a number: {r.raw}")


def _v3_refs(msg: Message, res: Result) -> None:
    for r in msg.records:
        if r.kind == "ref":
            for v in r.kv.values():
                if not (is_valid_ref(v) or is_sloc_ref(v)):
                    res.errors.append(f"V3: invalid ref format: {v}")
    deps = msg.headers.get("deps")
    if deps:
        for d in deps.split(","):
            d = d.strip()
            if not d or not (is_valid_ref(d) or is_sloc_ref(d) or _BARE_DEP.match(d)):
                res.errors.append(f"V3: invalid @deps entry: {d!r}")
    for k in ("p", "root", "parent"):
        v = msg.headers.get(k)
        if v and v.startswith("ref:") and not is_valid_ref(v):
            res.errors.append(f"V3: invalid ref in @{k}: {v}")


def _v6_rid_unique(msg: Message, res: Result) -> None:
    seen: set[str] = set()
    for r in msg.records:
        if r.rid:
            low = r.rid.lower()
            if low in seen:
                res.errors.append(f"V6: duplicate @rid: {r.rid}")
            seen.add(low)


def _v8_budget(msg: Message, res: Result) -> None:
    b = msg.headers.get("budget")
    if not b:
        return
    bm = _BUDGET.match(b)
    if not bm:
        res.errors.append(f"V8: invalid @budget format: {b}")
        return
    limit, cur = float(bm.group(1)), bm.group(2)
    total = 0.0
    for r in msg.records:
        if r.kind == "cost" and r.kv.get("cur") == cur:
            try:
                total += float(r.kv.get("val", "0"))
            except ValueError:
                pass
    if total > limit:
        res.errors.append(f"V8: total cost {total} {cur} exceeds budget {limit} {cur}")


def _v9_tool_chain(msg: Message, res: Result, strict: bool) -> None:
    call_rids = {r.rid.lower() for r in msg.records if r.kind == "call" and r.rid}
    for r in msg.records:
        if r.kind == "call" and "tool" not in r.kv:
            res.errors.append(f"V9: #call missing 'tool': {r.raw}")
        elif r.kind == "ret":
            if "call" not in r.kv:
                res.errors.append(f"V9: #ret missing 'call': {r.raw}")
            elif r.kv["call"].lower() not in call_rids:
                _emit(res, strict, f"V9: #ret references unknown call '{r.kv['call']}': {r.raw}")
            status = r.kv.get("status")
            if status is None:
                res.errors.append(f"V9: #ret missing 'status': {r.raw}")
            elif status not in ("ok", "err"):
                res.errors.append(f"V9: #ret status must be ok|err: {r.raw}")
        elif r.kind == "think" and "summary" not in r.kv:
            res.errors.append(f"V9: #think missing 'summary': {r.raw}")
        elif r.kind == "edit":
            if "file" not in r.kv:
                res.errors.append(f"V9: #edit missing 'file': {r.raw}")
            ch = r.kv.get("changes")
            if ch is None or not ch.isdigit() or int(ch) < 1:
                res.errors.append(f"V9: #edit 'changes' must be a positive integer: {r.raw}")


def _v11_turn_markers(msg: Message, res: Result) -> None:
    ids: set[str] = set()
    refs: list[tuple[str, str]] = []
    for r in msg.records:
        if r.kind == "marker":
            if r.name in ids:
                res.errors.append(f"V11: duplicate turn marker {r.name}")
            ids.add(r.name)
            if r.parent and r.parent != "-":
                refs.append((r.parent, "parent"))
        if r.m:
            refs.append((r.m, "@m"))
    if ids:
        for ref_id, kind in refs:
            if ref_id not in ids:
                res.errors.append(f"V11: {kind}={ref_id} references undeclared turn marker")


def _v12_columnar(msg: Message, res: Result) -> None:
    for blk in msg.blocks:
        label = f"#{blk.rtype}[{','.join(blk.columns)}]"
        if blk.rtype in COLUMNAR_FORBIDDEN:
            res.errors.append(f"V12: columnar form not allowed for #{blk.rtype} (key is data): {label}")
        if not blk.columns or any(not re.fullmatch(r"[a-z][a-z0-9_]*", c) for c in blk.columns):
            res.errors.append(f"V12: malformed column list: {label}")
            continue
        if len(set(blk.columns)) != len(blk.columns):
            res.errors.append(f"V12: duplicate column key in {label}")
        if not blk.rows:
            res.warnings.append(f"V12: columnar block has no rows: {label}")
        for row in blk.rows:
            if len(row) != len(blk.columns):
                vals = " ".join(('"%s"' % v if q else v) for v, q in row)
                res.errors.append(
                    f"V12: row has {len(row)} field(s), expected {len(blk.columns)} for {label}: {vals}"
                )


def _emit(res: Result, as_error: bool, msg: str) -> None:
    (res.errors if as_error else res.warnings).append(msg)
