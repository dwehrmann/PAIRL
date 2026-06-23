"""PAIRL v1.5 data model and parser.

Parses a PAIRL message (headers + body records) into a typed AST, including
v1.3 turn markers, v1.4 short references, and v1.5 columnar record blocks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

SPEC_VERSION = "1.5"

# Record types whose key schema is fixed (columnar-eligible). #fact/#ref have a
# variable key (the key is data) and are not columnar.
FIXED_SCHEMA_TYPES = {"evid", "rule", "cost", "quota", "call", "ret", "think", "edit"}
COLUMNAR_FORBIDDEN = {"fact", "ref"}

_COL_HEADER = re.compile(r"^#([a-z][a-z0-9_]*)\[([^\]]*)\]$")
_COMPACT_MARKER = re.compile(r"^#([uas])([0-9]{1,7})$")
_MSG_MARKER = re.compile(r"^#msg\s+(\S+)\s+r=(\S+)\s+parent=(\S+)\s*$")
_INTENT = re.compile(r"^([a-z0-9]{2,4}|[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*)+)(\{.*\})?(\s+@.*)?$")
_TRAILING_TAG = re.compile(r"@(m|rid)=([^\s]+)")


@dataclass
class Record:
    """A single body record (or a columnar row expanded to a record)."""

    kind: str                      # fact, ref, evid, rule, cost, quota, call, ret, think, edit, req, rpt, s, intent, marker
    name: Optional[str] = None     # intent name; record type tag; marker id
    kv: dict[str, str] = field(default_factory=dict)
    rid: Optional[str] = None
    m: Optional[str] = None        # @m= turn binding
    raw: str = ""
    from_columnar: bool = False
    # marker-specific
    role: Optional[str] = None
    parent: Optional[str] = None
    # positional payload for records with no key=value body, e.g. #s <phase>:<progress>
    arg: Optional[str] = None


@dataclass
class ColumnarBlock:
    rtype: str
    columns: list[str]
    rows: list[list[tuple[str, bool]]]  # each row: list of (value, was_quoted)
    raw_header: str = ""


@dataclass
class Message:
    headers: dict[str, str] = field(default_factory=dict)
    records: list[Record] = field(default_factory=list)
    blocks: list[ColumnarBlock] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)  # parse-level errors

    @property
    def msg_id(self) -> Optional[str]:
        return self.headers.get("id") or self.headers.get("mid")


def split_fields(s: str) -> list[tuple[str, bool]]:
    """Tokenize a whitespace-separated row into (value, was_quoted) fields.

    A double-quoted field (with \\" escaping) is one field and may contain spaces.
    """
    out: list[tuple[str, bool]] = []
    i, n = 0, len(s)
    while i < n:
        if s[i] == " ":
            i += 1
            continue
        if s[i] == '"':
            i += 1
            buf: list[str] = []
            while i < n:
                if s[i] == "\\" and i + 1 < n and s[i + 1] == '"':
                    buf.append('"')
                    i += 2
                    continue
                if s[i] == '"':
                    i += 1
                    break
                buf.append(s[i])
                i += 1
            out.append(("".join(buf), True))
        else:
            start = i
            while i < n and s[i] != " ":
                i += 1
            out.append((s[start:i], False))
    return out


def _parse_kvpairs(s: str) -> dict[str, str]:
    """Parse `key=value` pairs (space- or comma-separated), respecting quotes."""
    kv: dict[str, str] = {}
    i, n = 0, len(s)
    while i < n:
        if s[i] in " ,":
            i += 1
            continue
        # key
        kstart = i
        while i < n and s[i] not in "=":
            if s[i] in " ,":
                break
            i += 1
        key = s[kstart:i]
        if i >= n or s[i] != "=":
            # bare token, skip
            continue
        i += 1  # skip '='
        # value: quoted or atom up to space/comma
        if i < n and s[i] == '"':
            i += 1
            buf: list[str] = []
            while i < n:
                if s[i] == "\\" and i + 1 < n and s[i + 1] == '"':
                    buf.append('"')
                    i += 2
                    continue
                if s[i] == '"':
                    i += 1
                    break
                buf.append(s[i])
                i += 1
            kv[key] = "".join(buf)
        else:
            vstart = i
            while i < n and s[i] not in " ,":
                i += 1
            kv[key] = s[vstart:i]
    return kv


def _strip_trailing_tags(line: str) -> tuple[str, Optional[str], Optional[str]]:
    """Return (line_without_tags, m, rid)."""
    m_val = rid_val = None
    # iteratively peel trailing @m=/@rid= tokens
    while True:
        mt = re.search(r"\s+@(m|rid)=([^\s]+)\s*$", line)
        if not mt:
            break
        if mt.group(1) == "rid":
            rid_val = mt.group(2)
        else:
            m_val = mt.group(2)
        line = line[: mt.start()]
    return line.rstrip(), m_val, rid_val


def parse(text: str) -> Message:
    msg = Message()
    parts = text.strip("\n").split("\n\n", 1)
    if len(parts) != 2:
        # tolerate header-only or body-only, but record an error
        msg.errors.append("message must have a header block and a body separated by a blank line")
        if not parts:
            return msg
        # treat the single part as headers if it looks like headers, else body
        single = parts[0]
        if single.lstrip().startswith("@"):
            header_part, body_part = single, ""
        else:
            header_part, body_part = "", single
    else:
        header_part, body_part = parts

    for line in header_part.split("\n"):
        line = line.strip()
        if not line:
            continue
        if not line.startswith("@"):
            msg.errors.append(f"invalid header line (must start with @): {line}")
            continue
        m = re.match(r"@(\w+)\s+(.+)$", line)
        if m:
            msg.headers[m.group(1)] = m.group(2).strip()
        else:
            msg.errors.append(f"malformed header: {line}")

    lines = [ln.rstrip() for ln in body_part.split("\n")]
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line == "---":
            i += 1
            continue

        hm = _COL_HEADER.match(line)
        if hm:
            rtype = hm.group(1)
            cols = [c.strip() for c in hm.group(2).split(",")]
            rows: list[list[tuple[str, bool]]] = []
            i += 1
            while i < len(lines):
                row = lines[i].strip()
                if not row or row.startswith("#") or row == "---":
                    break
                fields, mval, ridval = _strip_trailing_tags(row)
                cells = split_fields(fields)
                rows.append(cells)
                rec = Record(kind=rtype, name=rtype, from_columnar=True, raw=lines[i],
                             rid=ridval, m=mval)
                for col, (val, _q) in zip(cols, cells):
                    rec.kv[col] = val
                msg.records.append(rec)
                i += 1
            msg.blocks.append(ColumnarBlock(rtype=rtype, columns=cols, rows=rows, raw_header=line))
            continue

        msg.records.append(_parse_record(line))
        i += 1

    return msg


def _parse_record(line: str) -> Record:
    raw = line
    cm = _COMPACT_MARKER.match(line)
    if cm:
        return Record(kind="marker", name=f"{cm.group(1)}{cm.group(2)}",
                      role=cm.group(1), raw=raw)
    mm = _MSG_MARKER.match(line)
    if mm:
        return Record(kind="marker", name=mm.group(1), role=mm.group(2),
                      parent=mm.group(3), raw=raw)

    body, mval, ridval = _strip_trailing_tags(line)

    if body.startswith("#"):
        mtype = re.match(r"^#([a-z][a-z0-9_]*)\s*(.*)$", body, re.DOTALL)
        if mtype:
            tag, rest = mtype.group(1), mtype.group(2)
            if tag == "s":
                # #s carries a positional <phase>:<progress> payload, not key=value (§7.5)
                return Record(kind="s", name="s", arg=rest.strip() or None,
                              rid=ridval, m=mval, raw=raw)
            return Record(kind=tag, name=tag, kv=_parse_kvpairs(rest),
                          rid=ridval, m=mval, raw=raw)

    # intent: name{params}
    im = _INTENT.match(body)
    if im:
        name = im.group(1)
        params = {}
        if im.group(2):
            inner = im.group(2)[1:-1]
            params = _parse_kvpairs(inner)
        return Record(kind="intent", name=name, kv=params, rid=ridval, m=mval, raw=raw)

    return Record(kind="unknown", raw=raw, rid=ridval, m=mval)
