//! PAIRL v1.5 parser and validator (rules V1–V12), standard library only.
//!
//! Parses a PAIRL message (headers + body records) into an AST — including v1.3
//! turn markers, v1.4 short references, and v1.5 columnar record blocks — and
//! checks the conformance rules.

pub const SPEC_VERSION: &str = "1.6";

const COLUMNAR_FORBIDDEN: [&str; 2] = ["fact", "ref"];

/// A single body record (or a columnar row expanded to a record).
#[derive(Debug, Clone, Default)]
pub struct Record {
    pub kind: String,
    pub name: Option<String>,
    pub kv: Vec<(String, String)>,
    pub rid: Option<String>,
    pub m: Option<String>,
    pub raw: String,
    pub from_columnar: bool,
    pub role: Option<String>,
    pub parent: Option<String>,
    /// Positional payload for records with no key=value body, e.g. #s <phase>:<progress>.
    pub arg: Option<String>,
}

impl Record {
    pub fn get(&self, key: &str) -> Option<&str> {
        self.kv.iter().find(|(k, _)| k == key).map(|(_, v)| v.as_str())
    }
    pub fn has(&self, key: &str) -> bool {
        self.kv.iter().any(|(k, _)| k == key)
    }
}

#[derive(Debug, Clone, Default)]
pub struct ColumnarBlock {
    pub rtype: String,
    pub columns: Vec<String>,
    /// Each row: list of (value, was_quoted).
    pub rows: Vec<Vec<(String, bool)>>,
}

#[derive(Debug, Clone, Default)]
pub struct Message {
    pub headers: Vec<(String, String)>,
    pub records: Vec<Record>,
    pub blocks: Vec<ColumnarBlock>,
    pub errors: Vec<String>,
}

impl Message {
    pub fn header(&self, key: &str) -> Option<&str> {
        self.headers.iter().find(|(k, _)| k == key).map(|(_, v)| v.as_str())
    }
    pub fn has_header(&self, key: &str) -> bool {
        self.headers.iter().any(|(k, _)| k == key)
    }
}

#[derive(Debug, Default)]
pub struct ValidationResult {
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
}

impl ValidationResult {
    pub fn valid(&self) -> bool {
        self.errors.is_empty()
    }
}

/// Tokenize a whitespace-separated row into (value, was_quoted) fields.
/// A double-quoted field (with `\"` escaping) is one field and may hold spaces.
pub fn split_fields(s: &str) -> Vec<(String, bool)> {
    let chars: Vec<char> = s.chars().collect();
    let mut out = Vec::new();
    let mut i = 0;
    let n = chars.len();
    while i < n {
        if chars[i] == ' ' {
            i += 1;
            continue;
        }
        if chars[i] == '"' {
            i += 1;
            let mut buf = String::new();
            while i < n {
                if chars[i] == '\\' && i + 1 < n && chars[i + 1] == '"' {
                    buf.push('"');
                    i += 2;
                    continue;
                }
                if chars[i] == '"' {
                    i += 1;
                    break;
                }
                buf.push(chars[i]);
                i += 1;
            }
            out.push((buf, true));
        } else {
            let start = i;
            while i < n && chars[i] != ' ' {
                i += 1;
            }
            out.push((chars[start..i].iter().collect(), false));
        }
    }
    out
}

fn parse_kvpairs(s: &str) -> Vec<(String, String)> {
    let chars: Vec<char> = s.chars().collect();
    let mut kv = Vec::new();
    let mut i = 0;
    let n = chars.len();
    while i < n {
        if chars[i] == ' ' || chars[i] == ',' {
            i += 1;
            continue;
        }
        let kstart = i;
        while i < n && chars[i] != '=' && chars[i] != ' ' && chars[i] != ',' {
            i += 1;
        }
        let key: String = chars[kstart..i].iter().collect();
        if i >= n || chars[i] != '=' {
            continue;
        }
        i += 1; // skip '='
        let val: String = if i < n && chars[i] == '"' {
            i += 1;
            let mut buf = String::new();
            while i < n {
                if chars[i] == '\\' && i + 1 < n && chars[i + 1] == '"' {
                    buf.push('"');
                    i += 2;
                    continue;
                }
                if chars[i] == '"' {
                    i += 1;
                    break;
                }
                buf.push(chars[i]);
                i += 1;
            }
            buf
        } else {
            let vstart = i;
            while i < n && chars[i] != ' ' && chars[i] != ',' {
                i += 1;
            }
            chars[vstart..i].iter().collect()
        };
        kv.push((key, val));
    }
    kv
}

/// Slice off trailing `@m=`/`@rid=` tags without disturbing the prefix.
fn strip_trailing_tags(line: &str) -> (String, Option<String>, Option<String>) {
    let mut s = line.trim_end().to_string();
    let mut m = None;
    let mut rid = None;
    loop {
        let trimmed = s.trim_end();
        if let Some(pos) = trimmed.rfind(char::is_whitespace) {
            let last = &trimmed[pos + 1..];
            if let Some(v) = last.strip_prefix("@rid=") {
                rid = Some(v.to_string());
                s = trimmed[..pos].to_string();
                continue;
            }
            if let Some(v) = last.strip_prefix("@m=") {
                m = Some(v.to_string());
                s = trimmed[..pos].to_string();
                continue;
            }
        }
        break;
    }
    (s.trim_end().to_string(), m, rid)
}

fn columnar_header(line: &str) -> Option<(String, Vec<String>)> {
    if !line.starts_with('#') || !line.ends_with(']') {
        return None;
    }
    let open = line.find('[')?;
    let ident = &line[1..open];
    if ident.is_empty() || !ident.chars().next().unwrap().is_ascii_lowercase() {
        return None;
    }
    if !ident.chars().all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_') {
        return None;
    }
    let cols_str = &line[open + 1..line.len() - 1];
    let cols: Vec<String> = cols_str.split(',').map(|c| c.trim().to_string()).collect();
    Some((ident.to_string(), cols))
}

fn is_compact_marker(line: &str) -> Option<(char, String)> {
    let b = line.as_bytes();
    if b.len() < 3 || b[0] != b'#' {
        return None;
    }
    let role = b[1] as char;
    if !matches!(role, 'u' | 'a' | 's') {
        return None;
    }
    let num = &line[2..];
    if num.is_empty() || num.len() > 7 || !num.chars().all(|c| c.is_ascii_digit()) {
        return None;
    }
    Some((role, num.to_string()))
}

/// Parse a PAIRL message into a `Message` AST.
pub fn parse(text: &str) -> Message {
    let mut msg = Message::default();
    let trimmed = text.trim_matches('\n');
    let (header_part, body_part) = match trimmed.split_once("\n\n") {
        Some((h, b)) => (h, b),
        None => {
            msg.errors
                .push("message must have a header block and a body separated by a blank line".into());
            if trimmed.trim_start().starts_with('@') {
                (trimmed, "")
            } else {
                ("", trimmed)
            }
        }
    };

    for raw in header_part.lines() {
        let line = raw.trim();
        if line.is_empty() {
            continue;
        }
        if !line.starts_with('@') {
            msg.errors.push(format!("invalid header line (must start with @): {line}"));
            continue;
        }
        let rest = &line[1..];
        if let Some(sp) = rest.find(char::is_whitespace) {
            let key = rest[..sp].to_string();
            let val = rest[sp..].trim().to_string();
            msg.headers.push((key, val));
        } else {
            msg.errors.push(format!("malformed header: {line}"));
        }
    }

    let lines: Vec<&str> = body_part.lines().collect();
    let mut i = 0;
    while i < lines.len() {
        let line = lines[i].trim();
        if line.is_empty() || line == "---" {
            i += 1;
            continue;
        }
        if let Some((rtype, columns)) = columnar_header(line) {
            let mut block = ColumnarBlock {
                rtype: rtype.clone(),
                columns: columns.clone(),
                rows: Vec::new(),
            };
            i += 1;
            while i < lines.len() {
                let row = lines[i].trim();
                if row.is_empty() || row.starts_with('#') || row == "---" {
                    break;
                }
                let (body, m, rid) = strip_trailing_tags(row);
                let cells = split_fields(&body);
                let mut rec = Record {
                    kind: rtype.clone(),
                    name: Some(rtype.clone()),
                    from_columnar: true,
                    raw: lines[i].to_string(),
                    m,
                    rid,
                    ..Default::default()
                };
                for (idx, col) in columns.iter().enumerate() {
                    if let Some((val, _)) = cells.get(idx) {
                        rec.kv.push((col.clone(), val.clone()));
                    }
                }
                block.rows.push(cells);
                msg.records.push(rec);
                i += 1;
            }
            msg.blocks.push(block);
            continue;
        }
        msg.records.push(parse_record(line));
        i += 1;
    }

    msg
}

fn parse_record(line: &str) -> Record {
    if let Some((role, num)) = is_compact_marker(line) {
        return Record {
            kind: "marker".into(),
            name: Some(format!("{role}{num}")),
            role: Some(role.to_string()),
            raw: line.to_string(),
            ..Default::default()
        };
    }
    if let Some(rest) = line.strip_prefix("#msg ") {
        let toks: Vec<&str> = rest.split_whitespace().collect();
        let id = toks.first().copied().unwrap_or("");
        let mut role = None;
        let mut parent = None;
        for t in &toks[1.min(toks.len())..] {
            if let Some(v) = t.strip_prefix("r=") {
                role = Some(v.to_string());
            } else if let Some(v) = t.strip_prefix("parent=") {
                parent = Some(v.to_string());
            }
        }
        return Record {
            kind: "marker".into(),
            name: Some(id.to_string()),
            role,
            parent,
            raw: line.to_string(),
            ..Default::default()
        };
    }

    let (body, m, rid) = strip_trailing_tags(line);

    if let Some(rest) = body.strip_prefix('#') {
        let split = rest.find(char::is_whitespace);
        let (tag, kvstr) = match split {
            Some(p) => (&rest[..p], &rest[p..]),
            None => (rest, ""),
        };
        if !tag.is_empty() && tag.chars().all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_') {
            if tag == "s" {
                // #s carries a positional <phase>:<progress> payload, not key=value (§7.5)
                let arg = kvstr.trim();
                return Record {
                    kind: "s".into(),
                    name: Some("s".into()),
                    arg: (!arg.is_empty()).then(|| arg.to_string()),
                    rid,
                    m,
                    raw: line.to_string(),
                    ..Default::default()
                };
            }
            return Record {
                kind: tag.to_string(),
                name: Some(tag.to_string()),
                kv: parse_kvpairs(kvstr),
                rid,
                m,
                raw: line.to_string(),
                ..Default::default()
            };
        }
    }

    // intent: name{params}
    if let Some(open) = body.find('{') {
        if body.ends_with('}') {
            let name = body[..open].to_string();
            let params = parse_kvpairs(&body[open + 1..body.len() - 1]);
            return Record {
                kind: "intent".into(),
                name: Some(name),
                kv: params,
                rid,
                m,
                raw: line.to_string(),
                ..Default::default()
            };
        }
    }
    if !body.is_empty() && !body.starts_with('#') {
        return Record {
            kind: "intent".into(),
            name: Some(body.clone()),
            rid,
            m,
            raw: line.to_string(),
            ..Default::default()
        };
    }

    Record {
        kind: "unknown".into(),
        raw: line.to_string(),
        rid,
        m,
        ..Default::default()
    }
}

/// Check whether `s` contains a run of ≥`min_len` consecutive hex digits.
/// Mirrors the Python/TypeScript regex `[a-fA-F0-9]{12,}`.
fn contains_hex_run(s: &str, min_len: usize) -> bool {
    let mut run = 0usize;
    for c in s.chars() {
        if c.is_ascii_hexdigit() {
            run += 1;
            if run >= min_len {
                return true;
            }
        } else {
            run = 0;
        }
    }
    false
}

fn is_valid_ref(v: &str) -> bool {
    if !v.starts_with("ref:") || v.contains(' ') {
        return false;
    }
    let main = v.split('#').next().unwrap_or(v);
    let parts: Vec<&str> = main.split(':').collect();
    if parts.len() < 3 {
        return false;
    }
    // ns must be non-empty alnum/_/-
    !parts[1].is_empty()
        && parts[1].chars().all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
        && parts[2..].iter().all(|p| !p.is_empty())
}

fn is_sloc_ref(v: &str) -> bool {
    let mut it = v.chars();
    if it.next() != Some('@') {
        return false;
    }
    let rest: String = it.collect();
    let (id, frag) = match rest.split_once('#') {
        Some((a, b)) => (a, Some(b)),
        None => (rest.as_str(), None),
    };
    if id.is_empty() || id.len() > 8 || !id.chars().all(|c| c.is_ascii_alphanumeric()) {
        return false;
    }
    if let Some(f) = frag {
        if f.is_empty() || f.len() > 8 || !f.chars().all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-') {
            return false;
        }
    }
    true
}

fn is_bare_dep(v: &str) -> bool {
    let (id, frag) = match v.split_once('#') {
        Some((a, b)) => (a, Some(b)),
        None => (v, None),
    };
    if id.is_empty() || id.len() > 8 || !id.chars().all(|c| c.is_ascii_alphanumeric()) {
        return false;
    }
    if let Some(f) = frag {
        if f.is_empty() || !f.chars().all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-') {
            return false;
        }
    }
    true
}

fn parse_budget(b: &str) -> Option<(f64, String)> {
    let split = b.find(|c: char| c.is_ascii_alphabetic())?;
    let (num, unit) = b.split_at(split);
    let val: f64 = num.parse().ok()?;
    if unit.is_empty() || unit.len() > 16 || !unit.chars().all(|c| c.is_ascii_alphabetic()) {
        return None;
    }
    Some((val, unit.to_string()))
}

fn col_key_ok(c: &str) -> bool {
    !c.is_empty()
        && c.chars().next().unwrap().is_ascii_lowercase()
        && c.chars().all(|x| x.is_ascii_lowercase() || x.is_ascii_digit() || x == '_')
}

/// Validate a parsed message against rules V1–V12.
pub fn validate(msg: &Message, strict: bool) -> ValidationResult {
    let mut r = ValidationResult::default();
    r.errors.extend(msg.errors.iter().cloned());

    // Required headers
    for h in ["v", "ts"] {
        if !msg.has_header(h) {
            r.errors.push(format!("missing required header: @{h}"));
        }
    }
    if !msg.has_header("id") && !msg.has_header("mid") {
        r.errors.push("missing required header: @id (or legacy @mid)".into());
    }

    let has_rule = |name: &str| {
        msg.records
            .iter()
            .any(|rec| rec.kind == "rule" && rec.get(name) == Some("true"))
    };
    let emit = |r: &mut ValidationResult, as_err: bool, msg: String| {
        if as_err {
            r.errors.push(msg)
        } else {
            r.warnings.push(msg)
        }
    };

    // V1 — no new facts in intents (policy/heuristic)
    let enforce_v1 = strict && has_rule("no_new_facts");
    for rec in &msg.records {
        if rec.kind != "intent" {
            continue;
        }
        for (k, v) in &rec.kv {
            if v.contains("http://") || v.contains("https://") {
                emit(&mut r, enforce_v1, format!("V1: intent param '{k}' has a URL (move to #ref): {v}"));
            } else if contains_hex_run(v, 12)
            {
                emit(&mut r, enforce_v1, format!("V1: intent param '{k}' looks like a hash (move to #ref): {v}"));
            } else if k != "l" && k != "m" && v.chars().any(|c| c.is_ascii_digit()) {
                emit(&mut r, enforce_v1, format!("V1: intent param '{k}' has a number (consider #fact): {k}={v}"));
            }
        }
    }

    // V2 — evidence completeness
    for rec in &msg.records {
        if rec.kind != "evid" {
            continue;
        }
        let missing: Vec<&str> = ["claim", "src", "conf"].into_iter().filter(|k| !rec.has(k)).collect();
        if !missing.is_empty() {
            r.errors.push(format!("V2: #evid missing {}: {}", missing.join(", "), rec.raw));
            continue;
        }
        match rec.get("conf").unwrap().parse::<f64>() {
            Ok(c) if !(0.0..=1.0).contains(&c) => {
                r.errors.push(format!("V2: #evid conf must be in [0,1]: {}", rec.raw))
            }
            Err(_) => r.errors.push(format!("V2: #evid conf is not a number: {}", rec.raw)),
            _ => {}
        }
    }

    // V3 — ref format
    for rec in &msg.records {
        if rec.kind == "ref" {
            for (_, v) in &rec.kv {
                if !(is_valid_ref(v) || is_sloc_ref(v)) {
                    r.errors.push(format!("V3: invalid ref format: {v}"));
                }
            }
        }
    }
    if let Some(deps) = msg.header("deps") {
        for d in deps.split(',') {
            let d = d.trim();
            if d.is_empty() || !(is_valid_ref(d) || is_sloc_ref(d) || is_bare_dep(d)) {
                r.errors.push(format!("V3: invalid @deps entry: {d:?}"));
            }
        }
    }

    // V6 — RID uniqueness
    let mut seen: Vec<String> = Vec::new();
    for rec in &msg.records {
        if let Some(rid) = &rec.rid {
            let low = rid.to_lowercase();
            if seen.contains(&low) {
                r.errors.push(format!("V6: duplicate @rid: {rid}"));
            }
            seen.push(low);
        }
    }

    // V8 — budget compliance
    if let Some(b) = msg.header("budget") {
        match parse_budget(b) {
            None => r.errors.push(format!("V8: invalid @budget format: {b}")),
            Some((limit, cur)) => {
                let mut total = 0.0;
                for rec in &msg.records {
                    if rec.kind == "cost" && rec.get("cur") == Some(cur.as_str()) {
                        if let Some(v) = rec.get("val").and_then(|x| x.parse::<f64>().ok()) {
                            total += v;
                        }
                    }
                }
                if total > limit {
                    r.errors.push(format!("V8: total cost {total} {cur} exceeds budget {limit} {cur}"));
                }
            }
        }
    }

    // V9 — tool chain integrity
    let call_rids: Vec<String> = msg
        .records
        .iter()
        .filter(|rec| rec.kind == "call")
        .filter_map(|rec| rec.rid.as_ref().map(|s| s.to_lowercase()))
        .collect();
    for rec in &msg.records {
        match rec.kind.as_str() {
            "call" if !rec.has("tool") => r.errors.push(format!("V9: #call missing 'tool': {}", rec.raw)),
            "ret" => {
                match rec.get("call") {
                    None => r.errors.push(format!("V9: #ret missing 'call': {}", rec.raw)),
                    Some(c) if !call_rids.contains(&c.to_lowercase()) => {
                        emit(&mut r, strict, format!("V9: #ret references unknown call '{c}': {}", rec.raw))
                    }
                    _ => {}
                }
                match rec.get("status") {
                    None => r.errors.push(format!("V9: #ret missing 'status': {}", rec.raw)),
                    Some(s) if s != "ok" && s != "err" => {
                        r.errors.push(format!("V9: #ret status must be ok|err: {}", rec.raw))
                    }
                    _ => {}
                }
            }
            "think" if !rec.has("summary") => r.errors.push(format!("V9: #think missing 'summary': {}", rec.raw)),
            "edit" => {
                if !rec.has("file") {
                    r.errors.push(format!("V9: #edit missing 'file': {}", rec.raw));
                }
                let ok = rec
                    .get("changes")
                    .and_then(|c| c.parse::<i64>().ok())
                    .map(|n| n >= 1)
                    .unwrap_or(false);
                if !ok {
                    r.errors.push(format!("V9: #edit 'changes' must be a positive integer: {}", rec.raw));
                }
            }
            _ => {}
        }
    }

    // V11 — turn marker integrity
    let mut ids: Vec<String> = Vec::new();
    let mut refs: Vec<(String, &str)> = Vec::new();
    for rec in &msg.records {
        if rec.kind == "marker" {
            if let Some(name) = &rec.name {
                if ids.contains(name) {
                    r.errors.push(format!("V11: duplicate turn marker {name}"));
                }
                ids.push(name.clone());
            }
            if let Some(p) = &rec.parent {
                if p != "-" {
                    refs.push((p.clone(), "parent"));
                }
            }
        }
        if let Some(m) = &rec.m {
            refs.push((m.clone(), "@m"));
        }
    }
    if !ids.is_empty() {
        for (id, kind) in &refs {
            if !ids.contains(id) {
                r.errors.push(format!("V11: {kind}={id} references undeclared turn marker"));
            }
        }
    }

    // V12 — columnar block integrity
    for blk in &msg.blocks {
        let label = format!("#{}[{}]", blk.rtype, blk.columns.join(","));
        if COLUMNAR_FORBIDDEN.contains(&blk.rtype.as_str()) {
            r.errors.push(format!("V12: columnar form not allowed for #{} (key is data): {label}", blk.rtype));
        }
        if blk.columns.is_empty() || blk.columns.iter().any(|c| !col_key_ok(c)) {
            r.errors.push(format!("V12: malformed column list: {label}"));
            continue;
        }
        let mut uniq = blk.columns.clone();
        uniq.sort();
        uniq.dedup();
        if uniq.len() != blk.columns.len() {
            r.errors.push(format!("V12: duplicate column key in {label}"));
        }
        if blk.rows.is_empty() {
            r.warnings.push(format!("V12: columnar block has no rows: {label}"));
        }
        for row in &blk.rows {
            if row.len() != blk.columns.len() {
                r.errors.push(format!(
                    "V12: row has {} field(s), expected {} for {label}",
                    row.len(),
                    blk.columns.len()
                ));
            }
        }
    }

    r
}
