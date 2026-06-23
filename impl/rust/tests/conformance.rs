//! Runs the shared cross-implementation conformance corpus (impl/conformance).
//! Rust has no canonical hasher (std only), so it checks validity + error
//! substrings; Python/TypeScript additionally check the SHA-256 hashes.

use pairl::{parse, validate};

type Case = (String, bool, bool, String, String); // name, strict, valid, hash, substr

fn run(cur: &Option<Case>, body: &str, failures: &mut Vec<String>) {
    let Some((name, strict, valid, _hash, substr)) = cur else { return };
    let msg = parse(body);
    let res = validate(&msg, *strict);
    if res.valid() != *valid {
        failures.push(format!("{name}: expected valid={valid}, errors={:?}", res.errors));
    }
    if !*valid && substr != "-" && !res.errors.iter().any(|e| e.contains(substr.as_str())) {
        failures.push(format!("{name}: {substr:?} not found in {:?}", res.errors));
    }
}

#[test]
fn conformance_corpus() {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../conformance/cases.txt");
    let text = std::fs::read_to_string(path).expect("read conformance/cases.txt");

    let mut cur: Option<Case> = None;
    let mut body: Vec<&str> = Vec::new();
    let mut failures: Vec<String> = Vec::new();
    let mut count = 0;

    for line in text.split('\n') {
        if let Some(d) = line.strip_prefix("@@@CASE ") {
            run(&cur, &body.join("\n"), &mut failures);
            let f: Vec<&str> = d.splitn(5, '|').collect();
            assert_eq!(f.len(), 5, "malformed directive: {d}");
            cur = Some((f[0].into(), f[1] == "1", f[2] == "1", f[3].into(), f[4].into()));
            body.clear();
            count += 1;
        } else if cur.is_some() {
            body.push(line);
        }
    }
    run(&cur, &body.join("\n"), &mut failures);

    assert!(count > 0, "conformance corpus is empty");
    assert!(failures.is_empty(), "conformance failures:\n{}", failures.join("\n"));
}
