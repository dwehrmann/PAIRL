/** Canonicalization and SHA-256 hashing (SPEC §9). Columnar-invariant (§9.4a). */

import { createHash } from "node:crypto";
import type { Message, PairlRecord } from "./model.js";

const HEADER_ORDER = ["v", "id", "mid", "sid", "ts", "p", "parent", "root", "deps", "budget", "quota"];
const ATOM_OK = /^[A-Za-z0-9:._/@+-]+$/;

function fmtValue(v: string): string {
  return v === "" || !ATOM_OK.test(v) ? `"${v.replace(/"/g, '\\"')}"` : v;
}

export function serializeRecord(r: PairlRecord): string {
  if (r.kind === "marker") {
    if (r.parent !== undefined) return `#msg ${r.name} r=${r.role} parent=${r.parent}`;
    return `#${r.name}`;
  }
  let head: string;
  if (r.kind === "intent") {
    const params = Object.entries(r.kv).map(([k, v]) => `${k}=${fmtValue(v)}`).join(",");
    head = `${r.name}{${params}}`;
  } else if (r.kind === "s") {
    head = r.arg ? `#s ${r.arg}` : "#s";
  } else {
    const pairs = Object.entries(r.kv).map(([k, v]) => `${k}=${fmtValue(v)}`).join(" ");
    head = `#${r.name}${pairs ? " " + pairs : ""}`;
  }
  let trail = "";
  if (r.m) trail += ` @m=${r.m}`;
  if (r.rid) trail += ` @rid=${r.rid}`;
  return head + trail;
}

export function canonicalize(msg: Message, forHash = true): string {
  const lines: string[] = [];
  const present = Object.keys(msg.headers);
  const ordered = HEADER_ORDER.filter((k) => k in msg.headers);
  ordered.push(...present.filter((k) => !HEADER_ORDER.includes(k) && k !== "hash").sort());
  if (!forHash && "hash" in msg.headers) ordered.push("hash");
  for (const k of ordered) lines.push(`@${k} ${msg.headers[k]}`);
  lines.push("");
  for (const r of msg.records) lines.push(serializeRecord(r)); // columnar already expanded
  return lines.join("\n") + "\n";
}

export function computeHash(msg: Message): string {
  return createHash("sha256").update(canonicalize(msg, true), "utf8").digest("hex");
}

export function hashRef(msg: Message): string {
  return `ref:hash:sha256:${computeHash(msg)}`;
}
