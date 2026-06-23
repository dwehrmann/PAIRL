import { describe, expect, it } from "vitest";
import { parse, validate, computeHash, render, encode, decode } from "../src/index.js";

const HEADER = "@v 1\n@id m1\n@ts 2026-06-22T10:00:00.000+02:00\n\n";
const msg = (body: string) => parse(HEADER + body);

describe("parse", () => {
  it("parses headers and records", () => {
    const m = msg("req{t=demo,s=f,l=1} @rid=a1\n#fact deadline=2026-02-05 @rid=f1\n");
    expect(m.headers.id).toBe("m1");
    expect(m.records[0]).toMatchObject({ kind: "intent", name: "req", rid: "a1" });
    expect(m.records[0].kv.t).toBe("demo");
    expect(m.records[1]).toMatchObject({ kind: "fact" });
    expect(m.records[1].kv.deadline).toBe("2026-02-05");
  });

  it("keeps quoted values with spaces/specials", () => {
    const m = msg('#evid claim="cost = 60% lower, broadly" src=s1 conf=0.8\n');
    expect(m.records[0].kv.claim).toBe("cost = 60% lower, broadly");
  });

  it("parses + expands columnar blocks", () => {
    const m = msg('#evid[claim,src,conf]\n"a b happened" s1 0.85\n"c d" s2 0.90\n');
    expect(m.blocks).toHaveLength(1);
    expect(m.records).toHaveLength(2);
    expect(m.records.every((r) => r.kind === "evid" && r.fromColumnar)).toBe(true);
    expect(m.records[0].kv).toEqual({ claim: "a b happened", src: "s1", conf: "0.85" });
  });

  it("parses turn markers", () => {
    const m = msg("#u1\nreq{t=x} @rid=a1\n#a2\nack{t=x} @rid=a2\n");
    expect(m.records.filter((r) => r.kind === "marker").map((r) => r.name)).toEqual(["u1", "a2"]);
  });
});

describe("validate (V1–V12)", () => {
  it("accepts a valid message", () => {
    expect(validate(msg('#evid claim="x" src=s1 conf=0.5\n#ref s1=ref:url:ap:2026-01-01\n')).valid).toBe(true);
  });
  it("V2: flags #evid missing conf", () => {
    const r = validate(msg('#evid[claim,src]\n"x" s1\n'));
    expect(r.valid).toBe(false);
    expect(r.errors.some((e) => e.includes("missing"))).toBe(true);
  });
  it("V12: flags columnar row field-count mismatch", () => {
    const r = validate(msg('#evid[claim,src,conf]\n"only two" s1\n'));
    expect(r.errors.some((e) => e.includes("expected 3"))).toBe(true);
  });
  it("V12: forbids columnar for #fact", () => {
    const r = validate(msg("#fact[key,val]\ndeadline 2026-02-05\n"));
    expect(r.errors.some((e) => e.includes("not allowed for #fact"))).toBe(true);
  });
  it("V6: flags duplicate @rid", () => {
    expect(validate(msg("#fact a=1 @rid=f1\n#fact b=2 @rid=f1\n")).errors.some((e) => e.includes("V6"))).toBe(true);
  });
  it("V8: flags budget overrun", () => {
    const m = parse("@v 1\n@id m1\n@ts 2026-06-22T10:00:00.000+02:00\n@budget 0.10USD\n\n#cost val=0.42 cur=USD\n");
    expect(validate(m).errors.some((e) => e.includes("V8"))).toBe(true);
  });
  it("V11: flags dangling @m=", () => {
    expect(validate(msg("#u1\nreq{t=x} @rid=a1\n#fact k=v @m=a9 @rid=f1\n")).errors.some((e) => e.includes("V11"))).toBe(true);
  });
});

describe("canonical + hash", () => {
  it("columnar and key=value forms hash identically", () => {
    const kv = msg('#evid claim="a b" src=s1 conf=0.5\n#evid claim="c d" src=s2 conf=0.6\n');
    const col = msg('#evid[claim,src,conf]\n"a b" s1 0.5\n"c d" s2 0.6\n');
    expect(computeHash(kv)).toBe(computeHash(col));
  });
  it("hash is 64 hex chars and stable across encode/decode", () => {
    const m = msg("#fact a=1\n");
    expect(computeHash(m)).toHaveLength(64);
    expect(computeHash(decode(encode(m)))).toBe(computeHash(m));
  });
});

describe("render", () => {
  it("includes facts and evidence verbatim", () => {
    const out = render(msg('rpt{t=report,s=f,l=2}\n#fact title="Q4"\n#evid claim="rev up" src=s1 conf=0.9\n'));
    expect(out).toContain("Q4");
    expect(out).toContain("rev up");
    expect(out).toContain("90%");
  });
});
