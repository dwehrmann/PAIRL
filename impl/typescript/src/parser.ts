/** PAIRL v1.5 parser: text -> Message AST (incl. columnar blocks, turn markers). */

import type { ColumnarBlock, Field, Message, PairlRecord } from "./model.js";

const COL_HEADER = /^#([a-z][a-z0-9_]*)\[([^\]]*)\]$/;
const COMPACT_MARKER = /^#([uas])([0-9]{1,7})$/;
const MSG_MARKER = /^#msg\s+(\S+)\s+r=(\S+)\s+parent=(\S+)\s*$/;
const INTENT = /^([a-z0-9]{2,4}|[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*)+)(\{[\s\S]*\})?(\s+@[\s\S]*)?$/;
const HASH_REC = /^#([a-z][a-z0-9_]*)\s*([\s\S]*)$/;

/** Tokenize a whitespace-separated row into fields (quoted strings = one field). */
export function splitFields(s: string): Field[] {
  const out: Field[] = [];
  let i = 0;
  const n = s.length;
  while (i < n) {
    if (s[i] === " ") { i++; continue; }
    if (s[i] === '"') {
      i++;
      let buf = "";
      while (i < n) {
        if (s[i] === "\\" && i + 1 < n && s[i + 1] === '"') { buf += '"'; i += 2; continue; }
        if (s[i] === '"') { i++; break; }
        buf += s[i]; i++;
      }
      out.push({ value: buf, quoted: true });
    } else {
      const start = i;
      while (i < n && s[i] !== " ") i++;
      out.push({ value: s.slice(start, i), quoted: false });
    }
  }
  return out;
}

function parseKvpairs(s: string): Record<string, string> {
  const kv: Record<string, string> = {};
  let i = 0;
  const n = s.length;
  while (i < n) {
    if (s[i] === " " || s[i] === ",") { i++; continue; }
    const kStart = i;
    while (i < n && s[i] !== "=" && s[i] !== " " && s[i] !== ",") i++;
    const key = s.slice(kStart, i);
    if (i >= n || s[i] !== "=") continue;
    i++; // skip '='
    if (i < n && s[i] === '"') {
      i++;
      let buf = "";
      while (i < n) {
        if (s[i] === "\\" && i + 1 < n && s[i + 1] === '"') { buf += '"'; i += 2; continue; }
        if (s[i] === '"') { i++; break; }
        buf += s[i]; i++;
      }
      kv[key] = buf;
    } else {
      const vStart = i;
      while (i < n && s[i] !== " " && s[i] !== ",") i++;
      kv[key] = s.slice(vStart, i);
    }
  }
  return kv;
}

function stripTrailingTags(line: string): { body: string; m?: string; rid?: string } {
  let m: string | undefined;
  let rid: string | undefined;
  let cur = line;
  for (;;) {
    const mt = /\s+@(m|rid)=(\S+)\s*$/.exec(cur);
    if (!mt) break;
    if (mt[1] === "rid") rid = mt[2];
    else m = mt[2];
    cur = cur.slice(0, mt.index);
  }
  return { body: cur.replace(/\s+$/, ""), m, rid };
}

export function parse(text: string): Message {
  const msg: Message = { headers: {}, records: [], blocks: [], errors: [] };
  const parts = text.replace(/^\n+|\n+$/g, "").split(/\n\n/);
  let headerPart: string;
  let bodyPart: string;
  if (parts.length < 2) {
    msg.errors.push("message must have a header block and a body separated by a blank line");
    if (parts[0]?.trimStart().startsWith("@")) { headerPart = parts[0]; bodyPart = ""; }
    else { headerPart = ""; bodyPart = parts[0] ?? ""; }
  } else {
    headerPart = parts[0];
    bodyPart = parts.slice(1).join("\n\n");
  }

  for (const rawLine of headerPart.split("\n")) {
    const line = rawLine.trim();
    if (!line) continue;
    if (!line.startsWith("@")) { msg.errors.push(`invalid header line (must start with @): ${line}`); continue; }
    const m = /^@(\w+)\s+(.+)$/.exec(line);
    if (m) msg.headers[m[1]] = m[2].trim();
    else msg.errors.push(`malformed header: ${line}`);
  }

  const lines = bodyPart.split("\n").map((l) => l.replace(/\s+$/, ""));
  let i = 0;
  while (i < lines.length) {
    const line = lines[i].trim();
    if (!line || line === "---") { i++; continue; }

    const hm = COL_HEADER.exec(line);
    if (hm) {
      const rtype = hm[1];
      const columns = hm[2].split(",").map((c) => c.trim());
      const rows: Field[][] = [];
      const block: ColumnarBlock = { rtype, columns, rows, rawHeader: line };
      i++;
      while (i < lines.length) {
        const row = lines[i].trim();
        if (!row || row.startsWith("#") || row === "---") break;
        const { body, m, rid } = stripTrailingTags(row);
        const cells = splitFields(body);
        rows.push(cells);
        const rec: PairlRecord = { kind: rtype, name: rtype, kv: {}, raw: lines[i], fromColumnar: true, m, rid };
        columns.forEach((col, idx) => { if (idx < cells.length) rec.kv[col] = cells[idx].value; });
        msg.records.push(rec);
        i++;
      }
      msg.blocks.push(block);
      continue;
    }

    msg.records.push(parseRecord(line));
    i++;
  }

  return msg;
}

function parseRecord(line: string): PairlRecord {
  const cm = COMPACT_MARKER.exec(line);
  if (cm) return { kind: "marker", name: `${cm[1]}${cm[2]}`, role: cm[1], kv: {}, raw: line };
  const mm = MSG_MARKER.exec(line);
  if (mm) return { kind: "marker", name: mm[1], role: mm[2], parent: mm[3], kv: {}, raw: line };

  const { body, m, rid } = stripTrailingTags(line);

  if (body.startsWith("#")) {
    const hr = HASH_REC.exec(body);
    if (hr) {
      // #s carries a positional <phase>:<progress> payload, not key=value (§7.5)
      if (hr[1] === "s") return { kind: "s", name: "s", kv: {}, arg: hr[2].trim() || undefined, rid, m, raw: line };
      return { kind: hr[1], name: hr[1], kv: parseKvpairs(hr[2]), rid, m, raw: line };
    }
  }

  const im = INTENT.exec(body);
  if (im) {
    const name = im[1];
    const kv = im[2] ? parseKvpairs(im[2].slice(1, -1)) : {};
    return { kind: "intent", name, kv, rid, m, raw: line };
  }

  return { kind: "unknown", kv: {}, rid, m, raw: line };
}
