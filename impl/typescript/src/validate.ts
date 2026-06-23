/** PAIRL v1.5 validation rules (V1–V12). */

import { COLUMNAR_FORBIDDEN, type Message, type PairlRecord } from "./model.js";

const REF = /^ref:[A-Za-z0-9_-]+:[^\s]+$/;
const SLOC = /^@[A-Za-z0-9]{1,8}(?:#[A-Za-z0-9_-]{1,8})?$/;
const BARE_DEP = /^[A-Za-z0-9]{1,8}(?:#[A-Za-z0-9_-]{1,8})?$/;
const BUDGET = /^([0-9]+(?:\.[0-9]+)?)([A-Za-z]{1,16})$/;
const COL_KEY = /^[a-z][a-z0-9_]*$/;
const NUMERIC_INTENT_KEYS = new Set(["l", "m"]);

export interface Result {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export function isValidRef(v: string): boolean {
  if (!v.startsWith("ref:") || v.includes(" ")) return false;
  const main = v.split("#")[0];
  return main.split(":").length >= 3 && REF.test(main);
}
export function isSlocRef(v: string): boolean {
  return SLOC.test(v);
}

export function validate(msg: Message, strict = false): Result {
  const errors: string[] = [...msg.errors];
  const warnings: string[] = [];
  const emit = (asErr: boolean, m: string) => (asErr ? errors : warnings).push(m);

  for (const h of ["v", "ts"]) if (!(h in msg.headers)) errors.push(`missing required header: @${h}`);
  if (!("id" in msg.headers) && !("mid" in msg.headers))
    errors.push("missing required header: @id (or legacy @mid)");

  const hasRule = (name: string) =>
    msg.records.some((r) => r.kind === "rule" && r.kv[name] === "true");

  // V1 — no new facts in intents (policy/heuristic)
  const enforceV1 = strict && hasRule("no_new_facts");
  for (const r of msg.records) {
    if (r.kind !== "intent") continue;
    for (const [k, v] of Object.entries(r.kv)) {
      if (/https?:\/\//.test(v)) emit(enforceV1, `V1: intent param '${k}' has a URL (move to #ref): ${v}`);
      else if (/[a-fA-F0-9]{12,}/.test(v)) emit(enforceV1, `V1: intent param '${k}' looks like a hash (move to #ref): ${v}`);
      else if (!NUMERIC_INTENT_KEYS.has(k) && /\d/.test(v)) emit(enforceV1, `V1: intent param '${k}' has a number (consider #fact): ${k}=${v}`);
    }
  }

  // V2 — evidence completeness
  for (const r of msg.records) {
    if (r.kind !== "evid") continue;
    const missing = ["claim", "src", "conf"].filter((k) => !(k in r.kv));
    if (missing.length) { errors.push(`V2: #evid missing ${missing.join(", ")}: ${r.raw}`); continue; }
    const c = Number(r.kv.conf);
    if (Number.isNaN(c)) errors.push(`V2: #evid conf is not a number: ${r.raw}`);
    else if (c < 0 || c > 1) errors.push(`V2: #evid conf must be in [0,1]: ${r.raw}`);
  }

  // V3 — ref format
  for (const r of msg.records) {
    if (r.kind === "ref")
      for (const v of Object.values(r.kv))
        if (!(isValidRef(v) || isSlocRef(v))) errors.push(`V3: invalid ref format: ${v}`);
  }
  if (msg.headers.deps)
    for (const d of msg.headers.deps.split(",").map((x) => x.trim()))
      if (!d || !(isValidRef(d) || isSlocRef(d) || BARE_DEP.test(d)))
        errors.push(`V3: invalid @deps entry: ${JSON.stringify(d)}`);

  // V6 — RID uniqueness
  const seen = new Set<string>();
  for (const r of msg.records) {
    if (!r.rid) continue;
    const low = r.rid.toLowerCase();
    if (seen.has(low)) errors.push(`V6: duplicate @rid: ${r.rid}`);
    seen.add(low);
  }

  // V8 — budget compliance
  if (msg.headers.budget) {
    const bm = BUDGET.exec(msg.headers.budget);
    if (!bm) errors.push(`V8: invalid @budget format: ${msg.headers.budget}`);
    else {
      const limit = Number(bm[1]);
      const cur = bm[2];
      let total = 0;
      for (const r of msg.records)
        if (r.kind === "cost" && r.kv.cur === cur) total += Number(r.kv.val ?? "0") || 0;
      if (total > limit) errors.push(`V8: total cost ${total} ${cur} exceeds budget ${limit} ${cur}`);
    }
  }

  // V9 — tool chain integrity
  const callRids = new Set(msg.records.filter((r) => r.kind === "call" && r.rid).map((r) => r.rid!.toLowerCase()));
  for (const r of msg.records) {
    if (r.kind === "call" && !("tool" in r.kv)) errors.push(`V9: #call missing 'tool': ${r.raw}`);
    else if (r.kind === "ret") {
      if (!("call" in r.kv)) errors.push(`V9: #ret missing 'call': ${r.raw}`);
      else if (!callRids.has(r.kv.call.toLowerCase())) emit(strict, `V9: #ret references unknown call '${r.kv.call}': ${r.raw}`);
      if (!("status" in r.kv)) errors.push(`V9: #ret missing 'status': ${r.raw}`);
      else if (r.kv.status !== "ok" && r.kv.status !== "err") errors.push(`V9: #ret status must be ok|err: ${r.raw}`);
    } else if (r.kind === "think" && !("summary" in r.kv)) errors.push(`V9: #think missing 'summary': ${r.raw}`);
    else if (r.kind === "edit") {
      if (!("file" in r.kv)) errors.push(`V9: #edit missing 'file': ${r.raw}`);
      const ch = r.kv.changes;
      if (!ch || !/^\d+$/.test(ch) || Number(ch) < 1) errors.push(`V9: #edit 'changes' must be a positive integer: ${r.raw}`);
    }
  }

  // V11 — turn marker integrity
  const ids = new Set<string>();
  const refs: Array<[string, string]> = [];
  for (const r of msg.records) {
    if (r.kind === "marker") {
      if (r.name && ids.has(r.name)) errors.push(`V11: duplicate turn marker ${r.name}`);
      if (r.name) ids.add(r.name);
      if (r.parent && r.parent !== "-") refs.push([r.parent, "parent"]);
    }
    if (r.m) refs.push([r.m, "@m"]);
  }
  if (ids.size)
    for (const [id, kind] of refs)
      if (!ids.has(id)) errors.push(`V11: ${kind}=${id} references undeclared turn marker`);

  // V12 — columnar block integrity
  for (const blk of msg.blocks) {
    const label = `#${blk.rtype}[${blk.columns.join(",")}]`;
    if (COLUMNAR_FORBIDDEN.has(blk.rtype)) errors.push(`V12: columnar form not allowed for #${blk.rtype} (key is data): ${label}`);
    if (!blk.columns.length || blk.columns.some((c) => !COL_KEY.test(c))) { errors.push(`V12: malformed column list: ${label}`); continue; }
    if (new Set(blk.columns).size !== blk.columns.length) errors.push(`V12: duplicate column key in ${label}`);
    if (!blk.rows.length) warnings.push(`V12: columnar block has no rows: ${label}`);
    for (const row of blk.rows)
      if (row.length !== blk.columns.length)
        errors.push(`V12: row has ${row.length} field(s), expected ${blk.columns.length} for ${label}`);
  }

  return { valid: errors.length === 0, errors, warnings };
}
