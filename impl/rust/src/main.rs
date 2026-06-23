//! CLI: pairl-validate [--strict] <file.pairl>

use std::process::ExitCode;

use pairl_validator::{parse, validate};

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let strict = args.iter().any(|a| a == "--strict");
    let file = args.iter().skip(1).find(|a| !a.starts_with('-'));

    let Some(path) = file else {
        eprintln!("usage: pairl-validate [--strict] <file.pairl>");
        return ExitCode::from(2);
    };

    let text = match std::fs::read_to_string(path) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("error: {e}");
            return ExitCode::from(2);
        }
    };

    let msg = parse(&text);
    let res = validate(&msg, strict);

    for e in &res.errors {
        println!("  ✗ {e}");
    }
    for w in &res.warnings {
        println!("  ⚠ {w}");
    }
    if res.valid() {
        println!("✓ PASSED — {path}");
        ExitCode::SUCCESS
    } else {
        println!("✗ FAILED — {path}");
        ExitCode::FAILURE
    }
}
