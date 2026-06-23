/** Deterministic PAIRL -> human-readable renderer (no LLM; faithful, §12). */

import { messageId, type Message, type PairlRecord } from "./model.js";

const INTENT_LABELS: Record<string, string> = {
  req: "Request", qst: "Question", ack: "Acknowledgement", pln: "Plan", nxt: "Next action",
  sum: "Summary", upd: "Status update", fin: "Done", blk: "Blocked", ctx: "Context",
  fnd: "Findings", evl: "Assessment", cmp: "Comparison", lst: "List", def: "Clarification",
  wrn: "Warning", agr: "Agreement", dis: "Disagreement", alt: "Alternative", emf: "Emphasis",
  cnt: "Contrast", rpt: "Report (unconfirmed)", off: "Official", inc: "Incident",
  apx: "Apology", thx: "Thanks", grt: "Greeting", cls: "Closing", bid: "Cost proposal",
};
const ROLE: Record<string, string> = { u: "User", a: "Assistant", s: "System" };

export function render(msg: Message): string {
  const out: string[] = [];
  out.push(`# PAIRL message ${messageId(msg) ?? "(no id)"}`);
  const meta: string[] = [];
  if (msg.headers.ts) meta.push(`time ${msg.headers.ts}`);
  if (msg.headers.p) meta.push(`in reply to ${msg.headers.p}`);
  if (msg.headers.budget) meta.push(`budget ${msg.headers.budget}`);
  if (meta.length) out.push("_" + meta.join(" · ") + "_");
  out.push("");

  for (const r of msg.records) {
    if (r.kind === "marker") {
      out.push(`## ${ROLE[r.role ?? ""] ?? r.role ?? "?"} (${r.name})`);
      continue;
    }
    const line = renderRecord(r);
    if (line) out.push(line);
  }
  return out.join("\n").replace(/\s+$/, "") + "\n";
}

function renderRecord(r: PairlRecord): string | null {
  switch (r.kind) {
    case "intent": {
      const label = INTENT_LABELS[r.name ?? ""] ?? r.name ?? "intent";
      let s = `- **${label}**`;
      if (r.kv.t) s += `: ${r.kv.t.replace(/_/g, " ")}`;
      if (r.kv.m === "!") s += " (urgent)";
      return s;
    }
    case "fact":
      return "  - " + Object.entries(r.kv).map(([k, v]) => `${k} = ${v}`).join("; ");
    case "evid": {
      let conf = r.kv.conf ?? "?";
      const n = Number(conf);
      if (!Number.isNaN(n)) conf = `${Math.round(n * 100)}%`;
      return `  - Evidence: "${r.kv.claim ?? ""}" — source ${r.kv.src ?? "?"}, confidence ${conf}`;
    }
    case "ref":
      return "  - Reference: " + Object.entries(r.kv).map(([k, v]) => `${k} → ${v}`).join("; ");
    case "rule":
      return "  - Rule: " + Object.entries(r.kv).map(([k, v]) => `${k}=${v}`).join(", ");
    case "cost":
      return `  - Cost: ${r.kv.val ?? "?"} ${r.kv.cur ?? ""}${r.kv.model ? ` (${r.kv.model})` : ""}`.trimEnd();
    case "quota": {
      const bits = [r.kv.type ?? "?"];
      if (r.kv.used && r.kv.total) bits.push(`used ${r.kv.used}/${r.kv.total}`);
      if (r.kv.rem) bits.push(`${r.kv.rem} remaining`);
      return "  - Quota: " + bits.join(", ");
    }
    case "call": return `  - Tool call: ${r.kv.tool ?? "?"}`;
    case "ret": return `  - Tool result (${r.kv.status ?? "?"})`;
    case "think": return `  - Reasoning: ${r.kv.summary ?? ""}`;
    case "edit": return `  - Edit: ${r.kv.file ?? "?"} (${r.kv.changes ?? "?"} changes)`;
    default: return null;
  }
}
