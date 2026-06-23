import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { computeHash, parse, validate } from "../src/index.js";

const here = dirname(fileURLToPath(import.meta.url));
const CASES = resolve(here, "../../conformance/cases.txt");

interface Case {
  name: string; strict: boolean; valid: boolean; hash: string; substr: string; body: string;
}

function load(): Case[] {
  const text = readFileSync(CASES, "utf8");
  const cases: Case[] = [];
  let cur: Omit<Case, "body"> | null = null;
  let body: string[] = [];
  for (const line of text.split("\n")) {
    if (line.startsWith("@@@CASE ")) {
      if (cur) cases.push({ ...cur, body: body.join("\n") });
      const [name, strict, valid, hash, substr] = line.slice(8).split("|");
      cur = { name, strict: strict === "1", valid: valid === "1", hash, substr };
      body = [];
    } else if (cur) {
      body.push(line);
    }
  }
  if (cur) cases.push({ ...cur, body: body.join("\n") });
  return cases;
}

describe("cross-implementation conformance corpus", () => {
  const cases = load();
  it("corpus is non-empty", () => expect(cases.length).toBeGreaterThan(0));
  for (const c of cases) {
    it(c.name, () => {
      const msg = parse(c.body);
      const res = validate(msg, c.strict);
      expect(res.valid, `errors=${JSON.stringify(res.errors)}`).toBe(c.valid);
      if (!c.valid && c.substr !== "-") {
        expect(res.errors.some((e) => e.includes(c.substr))).toBe(true);
      }
      if (c.hash !== "-") {
        expect(computeHash(msg)).toBe(c.hash);
      }
    });
  }
});
