use pairl::{parse, validate};

const HEADER: &str = "@v 1\n@id m1\n@ts 2026-06-22T10:00:00.000+02:00\n\n";

fn msg(body: &str) -> pairl::Message {
    parse(&format!("{HEADER}{body}"))
}

#[test]
fn parses_headers_and_records() {
    let m = msg("req{t=demo,s=f,l=1} @rid=a1\n#fact deadline=2026-02-05 @rid=f1\n");
    assert_eq!(m.header("id"), Some("m1"));
    assert_eq!(m.records[0].kind, "intent");
    assert_eq!(m.records[0].name.as_deref(), Some("req"));
    assert_eq!(m.records[0].get("t"), Some("demo"));
    assert_eq!(m.records[0].rid.as_deref(), Some("a1"));
    assert_eq!(m.records[1].kind, "fact");
    assert_eq!(m.records[1].get("deadline"), Some("2026-02-05"));
}

#[test]
fn keeps_quoted_values_with_spaces() {
    let m = msg("#evid claim=\"cost = 60% lower, broadly\" src=s1 conf=0.8\n");
    assert_eq!(m.records[0].get("claim"), Some("cost = 60% lower, broadly"));
    assert_eq!(m.records[0].get("conf"), Some("0.8"));
}

#[test]
fn parses_and_expands_columnar() {
    let m = msg("#evid[claim,src,conf]\n\"a b happened\" s1 0.85\n\"c d\" s2 0.90\n");
    assert_eq!(m.blocks.len(), 1);
    assert_eq!(m.records.len(), 2);
    assert!(m.records.iter().all(|r| r.kind == "evid" && r.from_columnar));
    assert_eq!(m.records[0].get("claim"), Some("a b happened"));
    assert_eq!(m.records[0].get("conf"), Some("0.85"));
}

#[test]
fn parses_turn_markers() {
    let m = msg("#u1\nreq{t=x} @rid=a1\n#a2\nack{t=x} @rid=a2\n");
    let names: Vec<_> = m
        .records
        .iter()
        .filter(|r| r.kind == "marker")
        .filter_map(|r| r.name.clone())
        .collect();
    assert_eq!(names, vec!["u1", "a2"]);
}

#[test]
fn accepts_valid_message() {
    let m = msg("#evid claim=\"x\" src=s1 conf=0.5\n#ref s1=ref:url:ap:2026-01-01\n");
    assert!(validate(&m, false).valid());
}

#[test]
fn v2_flags_missing_conf() {
    let r = validate(&msg("#evid[claim,src]\n\"x\" s1\n"), false);
    assert!(!r.valid());
    assert!(r.errors.iter().any(|e| e.contains("missing")));
}

#[test]
fn v12_flags_field_count_mismatch() {
    let r = validate(&msg("#evid[claim,src,conf]\n\"only two\" s1\n"), false);
    assert!(r.errors.iter().any(|e| e.contains("expected 3")));
}

#[test]
fn v12_forbids_columnar_for_fact() {
    let r = validate(&msg("#fact[key,val]\ndeadline 2026-02-05\n"), false);
    assert!(r.errors.iter().any(|e| e.contains("not allowed for #fact")));
}

#[test]
fn v6_flags_duplicate_rid() {
    let r = validate(&msg("#fact a=1 @rid=f1\n#fact b=2 @rid=f1\n"), false);
    assert!(r.errors.iter().any(|e| e.contains("V6")));
}

#[test]
fn v8_flags_budget_overrun() {
    let m = parse("@v 1\n@id m1\n@ts 2026-06-22T10:00:00.000+02:00\n@budget 0.10USD\n\n#cost val=0.42 cur=USD\n");
    assert!(validate(&m, false).errors.iter().any(|e| e.contains("V8")));
}

#[test]
fn v11_flags_dangling_m_ref() {
    let r = validate(&msg("#u1\nreq{t=x} @rid=a1\n#fact k=v @m=a9 @rid=f1\n"), false);
    assert!(r.errors.iter().any(|e| e.contains("V11")));
}
