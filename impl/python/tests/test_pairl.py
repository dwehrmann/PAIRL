import unittest

from pairl import canonicalize, compute_hash, parse, render, validate

HEADER = "@v 1\n@id m1\n@ts 2026-06-22T10:00:00.000+02:00\n\n"


def msg(body: str):
    return parse(HEADER + body)


class TestParse(unittest.TestCase):
    def test_headers_and_records(self):
        m = msg("req{t=demo,s=f,l=1} @rid=a1\n#fact deadline=2026-02-05 @rid=f1\n")
        self.assertEqual(m.headers["id"], "m1")
        self.assertEqual(m.records[0].kind, "intent")
        self.assertEqual(m.records[0].name, "req")
        self.assertEqual(m.records[0].kv["t"], "demo")
        self.assertEqual(m.records[0].rid, "a1")
        self.assertEqual(m.records[1].kind, "fact")
        self.assertEqual(m.records[1].kv["deadline"], "2026-02-05")

    def test_quoted_value_with_spaces(self):
        m = msg('#evid claim="cost = 60% lower, broadly" src=s1 conf=0.8\n')
        self.assertEqual(m.records[0].kv["claim"], "cost = 60% lower, broadly")
        self.assertEqual(m.records[0].kv["conf"], "0.8")

    def test_columnar_parse_and_expand(self):
        m = msg('#evid[claim,src,conf]\n"a b happened" s1 0.85\n"c d" s2 0.90\n')
        self.assertEqual(len(m.blocks), 1)
        self.assertEqual(len(m.records), 2)
        self.assertTrue(all(r.kind == "evid" and r.from_columnar for r in m.records))
        self.assertEqual(m.records[0].kv, {"claim": "a b happened", "src": "s1", "conf": "0.85"})

    def test_turn_markers(self):
        m = msg("#u1\nreq{t=x} @rid=a1\n#a2\nack{t=x} @rid=a2\n")
        markers = [r for r in m.records if r.kind == "marker"]
        self.assertEqual([mk.name for mk in markers], ["u1", "a2"])


class TestValidate(unittest.TestCase):
    def test_valid_message(self):
        m = msg("#evid claim=\"x happened\" src=s1 conf=0.5\n#ref s1=ref:url:ap:2026-01-01\n")
        self.assertTrue(validate(m).valid)

    def test_evid_missing_conf(self):
        m = msg('#evid[claim,src]\n"x" s1\n')
        r = validate(m)
        self.assertFalse(r.valid)
        self.assertTrue(any("missing" in e for e in r.errors))

    def test_columnar_field_count_mismatch(self):
        m = msg('#evid[claim,src,conf]\n"only two" s1\n')
        r = validate(m)
        self.assertFalse(r.valid)
        self.assertTrue(any("expected 3" in e for e in r.errors))

    def test_columnar_forbidden_for_fact(self):
        m = msg("#fact[key,val]\ndeadline 2026-02-05\n")
        r = validate(m)
        self.assertFalse(r.valid)
        self.assertTrue(any("not allowed for #fact" in e for e in r.errors))

    def test_duplicate_rid(self):
        m = msg("#fact a=1 @rid=f1\n#fact b=2 @rid=f1\n")
        r = validate(m)
        self.assertFalse(r.valid)
        self.assertTrue(any("V6" in e for e in r.errors))

    def test_budget_exceeded(self):
        m = parse("@v 1\n@id m1\n@ts 2026-06-22T10:00:00.000+02:00\n@budget 0.10USD\n\n"
                  "#cost val=0.42 cur=USD\n")
        r = validate(m)
        self.assertFalse(r.valid)
        self.assertTrue(any("V8" in e for e in r.errors))

    def test_dangling_turn_ref(self):
        m = msg("#u1\nreq{t=x} @rid=a1\n#fact k=v @m=a9 @rid=f1\n")
        r = validate(m)
        self.assertFalse(r.valid)
        self.assertTrue(any("V11" in e for e in r.errors))


class TestCanonicalAndHash(unittest.TestCase):
    def test_columnar_and_kv_hash_identically(self):
        kv = msg('#evid claim="a b" src=s1 conf=0.5\n#evid claim="c d" src=s2 conf=0.6\n')
        col = msg('#evid[claim,src,conf]\n"a b" s1 0.5\n"c d" s2 0.6\n')
        self.assertEqual(compute_hash(kv), compute_hash(col))

    def test_hash_is_stable(self):
        m = msg("#fact a=1\n")
        self.assertEqual(compute_hash(m), compute_hash(parse(canonicalize(m, for_hash=False))))

    def test_hash_hex_length(self):
        self.assertEqual(len(compute_hash(msg("#fact a=1\n"))), 64)


class TestRender(unittest.TestCase):
    def test_render_contains_facts_and_evidence(self):
        out = render(msg('rpt{t=report,s=f,l=2}\n#fact title="Q4"\n#evid claim="rev up" src=s1 conf=0.9\n'))
        self.assertIn("Q4", out)
        self.assertIn("rev up", out)
        self.assertIn("90%", out)


if __name__ == "__main__":
    unittest.main()
