/** PAIRL v1.5 data model. */

export const SPEC_VERSION = "1.5";

/** Record types with a fixed key schema (columnar-eligible). */
export const FIXED_SCHEMA_TYPES = new Set(["evid", "rule", "cost", "quota", "call", "ret", "think", "edit"]);
/** Record types whose key is data — columnar is not allowed. */
export const COLUMNAR_FORBIDDEN = new Set(["fact", "ref"]);

export interface PairlRecord {
  kind: string; // fact, ref, evid, rule, cost, quota, call, ret, think, edit, req, rpt, s, intent, marker, unknown
  name?: string;
  kv: Record<string, string>;
  rid?: string;
  m?: string;
  raw: string;
  fromColumnar?: boolean;
  role?: string;
  parent?: string;
  /** Positional payload for records with no key=value body, e.g. #s <phase>:<progress>. */
  arg?: string;
}

export interface Field {
  value: string;
  quoted: boolean;
}

export interface ColumnarBlock {
  rtype: string;
  columns: string[];
  rows: Field[][];
  rawHeader: string;
}

export interface Message {
  headers: Record<string, string>;
  records: PairlRecord[];
  blocks: ColumnarBlock[];
  errors: string[];
}

export function messageId(msg: Message): string | undefined {
  return msg.headers.id ?? msg.headers.mid;
}
