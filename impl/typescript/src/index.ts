/** PAIRL v1.5 reference library: parse, serialize, validate, canonicalize, render. */

export { SPEC_VERSION, messageId } from "./model.js";
export type { Message, PairlRecord, ColumnarBlock, Field } from "./model.js";
export { parse, splitFields } from "./parser.js";
export { validate, isValidRef, isSlocRef } from "./validate.js";
export type { Result } from "./validate.js";
export { canonicalize, serializeRecord, computeHash, hashRef } from "./canonical.js";
export { render } from "./render.js";

import { parse } from "./parser.js";
import { canonicalize } from "./canonical.js";
import type { Message } from "./model.js";

/** Decode PAIRL text into a Message AST. */
export function decode(text: string): Message {
  return parse(text);
}

/** Encode a Message AST back to canonical PAIRL text (columnar expanded). */
export function encode(msg: Message): string {
  return canonicalize(msg, false);
}
