#!/usr/bin/env python3
"""
PAIRL v1.1 Validator

Reference validator for PAIRL message syntax and core validation rules.
Policy checks (for example V1 no-new-facts heuristics) are reported separately.

Usage:
    python validator.py <file.pairl>
    python validator.py --strict <file.pairl>
"""

import re
import sys
from typing import Dict, List, Optional, Set, Tuple


INTENT_PATTERN = re.compile(
    r"^([a-z0-9]{2,4}|[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*)+)"
    r"(?:\{([^}]*)\})?"
    r"(?:\s+@rid=([A-Za-z0-9]{1,8}))?$"
)
RID_PATTERN = re.compile(r"@rid=([A-Za-z0-9]{1,8})$")
KV_TOKEN_PATTERN = re.compile(r"\b([a-z][a-z0-9_]*)=([^\s]+)")
EVID_CONF_PATTERN = re.compile(r"\bconf=([0-9]+(?:\.[0-9]+)?)\b")
BUDGET_PATTERN = re.compile(r"^([0-9]+(?:\.[0-9]+)?)([A-Za-z]{1,16})$")
KNOWN_INTENT_NUMERIC_KEYS = {"l", "m"}


def split_ref(ref_value: str) -> Tuple[str, Optional[str]]:
    """Split ref into main and optional fragment."""
    if "#" not in ref_value:
        return ref_value, None
    main, fragment = ref_value.rsplit("#", 1)
    return main, fragment


def is_valid_ref(ref_value: str) -> bool:
    """Validate short or long ref syntax with optional record fragment."""
    if " " in ref_value or not ref_value.startswith("ref:"):
        return False

    main, fragment = split_ref(ref_value)
    if fragment is not None and not re.fullmatch(r"[A-Za-z0-9_-]{1,8}", fragment):
        return False

    parts = main.split(":")
    if len(parts) < 3:
        return False

    if parts[0] != "ref":
        return False

    ns = parts[1]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", ns):
        return False

    payload = parts[2:]
    # Short ref: ref:<ns>:<id>
    if len(payload) == 1:
        return payload[0] != ""

    # Long ref: ref:<ns>:<type>:<id-with-optional-colons>
    rtype = payload[0]
    rid = ":".join(payload[1:])
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", rtype):
        return False
    return rid != ""


class PAIRLMessage:
    """Represents a parsed PAIRL message."""

    def __init__(self, raw_text: str):
        self.headers: Dict[str, str] = {}
        self.records: List[str] = []
        self.raw_text = raw_text
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.parse(raw_text)

    def parse(self, text: str) -> None:
        """Parse PAIRL message into headers and records."""
        parts = text.strip().split("\n\n", 1)
        if len(parts) != 2:
            self.errors.append("Message must have header block and body separated by blank line")
            return

        header_part, body_part = parts

        for line in header_part.split("\n"):
            line = line.strip()
            if not line:
                continue
            if not line.startswith("@"):
                self.errors.append(f"Invalid header line (must start with @): {line}")
                continue
            match = re.match(r"@(\w+)\s+(.+)", line)
            if match:
                key, value = match.groups()
                self.headers[key] = value
            else:
                self.errors.append(f"Malformed header: {line}")

        for line in body_part.split("\n"):
            line = line.strip()
            if line:
                self.records.append(line)

    def _has_rule(self, rule_name: str) -> bool:
        for record in self.records:
            if record.startswith("#rule ") and f"{rule_name}=true" in record:
                return True
        return False

    def validate_required_headers(self) -> bool:
        required = ["v", "mid", "ts"]
        passed = True
        for field in required:
            if field not in self.headers:
                self.errors.append(f"Missing required header: @{field}")
                passed = False
        return passed

    def validate_intent_syntax(self) -> bool:
        """Validate intent name grammar and optional rid placement."""
        passed = True
        for record in self.records:
            if record.startswith("#"):
                continue
            if not INTENT_PATTERN.match(record):
                self.errors.append(f"Invalid intent record syntax: {record}")
                passed = False
        return passed

    def validate_no_new_facts_policy(self, strict: bool = False) -> bool:
        """
        V1 policy check: flag suspicious factual material in intents.
        This is a heuristic policy check, not base syntax validation.
        """
        passed = True
        enforce = strict and self._has_rule("no_new_facts")
        for record in self.records:
            if record.startswith("#"):
                continue
            match = INTENT_PATTERN.match(record)
            if not match:
                continue
            _, intent_args, _ = match.groups()
            if not intent_args:
                continue

            if re.search(r"https?://", intent_args):
                msg = f"Intent contains URL-like value (move to #ref): {intent_args}"
                if enforce:
                    self.errors.append(msg)
                    passed = False
                else:
                    self.warnings.append(msg)

            if re.search(r"[a-fA-F0-9]{12,}", intent_args):
                msg = f"Intent contains hash-like value (move to #ref): {intent_args}"
                if enforce:
                    self.errors.append(msg)
                    passed = False
                else:
                    self.warnings.append(msg)

            for key, value in [kv.split("=", 1) for kv in intent_args.split(",") if "=" in kv]:
                if key in KNOWN_INTENT_NUMERIC_KEYS:
                    continue
                if re.search(r"\d", value):
                    msg = f"Intent key '{key}' contains numeric value (consider #fact): {key}={value}"
                    if enforce:
                        self.errors.append(msg)
                        passed = False
                    else:
                        self.warnings.append(msg)
        return passed

    def validate_evidence(self) -> bool:
        """V2: Evidence records must have claim, src, conf and conf in [0,1]."""
        passed = True
        for record in self.records:
            if not record.startswith("#evid"):
                continue

            has_claim = "claim=" in record
            has_src = "src=" in record
            has_conf = "conf=" in record
            if not (has_claim and has_src and has_conf):
                missing = []
                if not has_claim:
                    missing.append("claim")
                if not has_src:
                    missing.append("src")
                if not has_conf:
                    missing.append("conf")
                self.errors.append(f"#evid missing required fields: {', '.join(missing)}")
                passed = False
                continue

            conf_match = EVID_CONF_PATTERN.search(record)
            if not conf_match:
                self.errors.append(f"#evid has invalid conf format: {record}")
                passed = False
                continue

            conf = float(conf_match.group(1))
            if conf < 0.0 or conf > 1.0:
                self.errors.append(f"#evid conf must be in [0,1]: {record}")
                passed = False

        return passed

    def validate_refs(self) -> bool:
        """V3: Validate refs in records and headers (including @deps lists)."""
        passed = True

        for record in self.records:
            if not record.startswith("#ref"):
                continue
            ref_values = re.findall(r"=\s*(ref:[^\s]+)", record)
            if not ref_values:
                self.errors.append(f"#ref record missing ref value: {record}")
                passed = False
                continue
            for ref_value in ref_values:
                if not is_valid_ref(ref_value):
                    self.errors.append(f"Invalid ref format: {ref_value}")
                    passed = False

        for key, value in self.headers.items():
            if key == "deps":
                for dep in value.split(","):
                    dep = dep.strip()
                    if not dep:
                        self.errors.append("Invalid @deps format: empty dependency entry")
                        passed = False
                        continue
                    if not is_valid_ref(dep):
                        self.errors.append(f"Invalid ref format in @deps: {dep}")
                        passed = False
                continue

            if value.startswith("ref:") and not is_valid_ref(value):
                self.errors.append(f"Invalid ref format in @{key}: {value}")
                passed = False

        return passed

    def validate_rid_uniqueness(self) -> bool:
        """V6: All RIDs within a message must be unique."""
        passed = True
        rids: Set[str] = set()
        for record in self.records:
            rid_match = RID_PATTERN.search(record)
            if not rid_match:
                continue
            rid = rid_match.group(1).lower()
            if rid in rids:
                self.errors.append(f"Duplicate RID: {rid}")
                passed = False
            else:
                rids.add(rid)
        return passed

    def validate_cost_and_quota(self) -> bool:
        """Validate required keys for #cost and #quota records."""
        passed = True
        for record in self.records:
            if record.startswith("#cost"):
                tokens = dict(KV_TOKEN_PATTERN.findall(record))
                if "val" not in tokens or "cur" not in tokens:
                    self.errors.append(f"#cost missing required keys val/cur: {record}")
                    passed = False
            if record.startswith("#quota"):
                tokens = dict(KV_TOKEN_PATTERN.findall(record))
                if "type" not in tokens or "total" not in tokens:
                    self.errors.append(f"#quota missing required keys type/total: {record}")
                    passed = False
        return passed

    def validate_budget(self, projected_cost: Optional[float] = None) -> Tuple[bool, str]:
        """V8: Budget format and simple cost-overrun check."""
        if "budget" not in self.headers:
            return True, "No budget specified"

        budget_str = self.headers["budget"]
        budget_match = BUDGET_PATTERN.match(budget_str)
        if not budget_match:
            self.errors.append(f"Invalid budget format: {budget_str}")
            return False, "Invalid budget format"

        budget_value = float(budget_match.group(1))
        currency = budget_match.group(2)

        if projected_cost is not None and projected_cost > budget_value:
            msg = f"Projected cost {projected_cost} exceeds budget {budget_value} {currency}"
            self.warnings.append(msg)
            return False, msg

        total_cost = 0.0
        for record in self.records:
            if not record.startswith("#cost"):
                continue
            cost_match = re.search(r"\bval=([0-9]+(?:\.[0-9]+)?)\s+cur=([A-Za-z0-9_]+)\b", record)
            if cost_match and cost_match.group(2) == currency:
                total_cost += float(cost_match.group(1))

        if total_cost > budget_value:
            msg = f"Total cost {total_cost} {currency} exceeds budget {budget_value} {currency}"
            self.errors.append(msg)
            return False, msg

        return True, f"Budget OK: {total_cost}/{budget_value} {currency} used"

    def validate(self, strict: bool = False) -> bool:
        """Run parser/validator checks."""
        if not self.validate_required_headers():
            return False

        self.validate_intent_syntax()
        self.validate_no_new_facts_policy(strict)
        self.validate_evidence()
        self.validate_refs()
        self.validate_rid_uniqueness()
        self.validate_cost_and_quota()
        self.validate_budget()

        return len(self.errors) == 0


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validator.py [--strict] <file.pairl>")
        sys.exit(1)

    strict = False
    filepath = sys.argv[1]

    if sys.argv[1] == "--strict":
        strict = True
        if len(sys.argv) < 3:
            print("Usage: python validator.py --strict <file.pairl>")
            sys.exit(1)
        filepath = sys.argv[2]

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    msg = PAIRLMessage(raw)

    print(f"Validating: {filepath}")
    print(f"Mode: {'strict' if strict else 'loose'}")
    print("-" * 50)

    if msg.errors:
        print(f"\n❌ Parse errors ({len(msg.errors)}):")
        for err in msg.errors:
            print(f"  - {err}")

    valid = msg.validate(strict)

    if msg.errors:
        print(f"\n❌ Validation errors ({len(msg.errors)}):")
        for err in msg.errors:
            print(f"  - {err}")

    if msg.warnings:
        print(f"\n⚠️  Warnings ({len(msg.warnings)}):")
        for warn in msg.warnings:
            print(f"  - {warn}")

    print(f"\n{'✓' if valid else '✗'} Validation {'PASSED' if valid else 'FAILED'}")

    print("\nMessage info:")
    print(f"  Version: {msg.headers.get('v', 'N/A')}")
    print(f"  ID: {msg.headers.get('mid', 'N/A')}")
    print(f"  Timestamp: {msg.headers.get('ts', 'N/A')}")
    print(f"  Records: {len(msg.records)}")
    if "budget" in msg.headers:
        print(f"  Budget: {msg.headers['budget']}")

    sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
