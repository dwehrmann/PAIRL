#!/usr/bin/env python3
"""
PAIRL v1.1 Validator

A reference validator for PAIRL messages.
Implements validation rules V1-V8 from the PAIRL specification.

Usage:
    python validator.py <file.pairl>
    python validator.py --strict <file.pairl>
"""

import re
import sys
from typing import Dict, List, Tuple, Optional


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
        parts = text.strip().split('\n\n', 1)
        if len(parts) != 2:
            self.errors.append("Message must have header block and body separated by blank line")
            return

        header_part, body_part = parts

        # Parse Headers
        for line in header_part.split('\n'):
            line = line.strip()
            if not line:
                continue
            if not line.startswith('@'):
                self.errors.append(f"Invalid header line (must start with @): {line}")
                continue
            matches = re.match(r'@(\w+)\s+(.+)', line)
            if matches:
                k, v = matches.groups()
                self.headers[k] = v
            else:
                self.errors.append(f"Malformed header: {line}")

        # Parse Body
        for line in body_part.split('\n'):
            line = line.strip()
            if line:
                self.records.append(line)

    def validate_required_headers(self) -> bool:
        """V0: Check required headers are present."""
        required = ['v', 'mid', 'ts']
        for field in required:
            if field not in self.headers:
                self.errors.append(f"Missing required header: @{field}")
                return False
        return True

    def validate_no_new_facts(self, strict: bool = False) -> bool:
        """V1: Intent records must not contain factual material (no digits, URLs, hex)."""
        passed = True
        for record in self.records:
            # Check if this is an intent record (not starting with #)
            if not record.startswith('#'):
                # Extract intent value part (inside {...})
                intent_match = re.match(r'(\w+)\{([^}]*)\}', record)
                if intent_match:
                    intent_name, intent_args = intent_match.groups()

                    # Check for digits
                    if re.search(r'\d', intent_args):
                        msg = f"Intent '{intent_name}' contains digits (move to #fact): {intent_args}"
                        if strict:
                            self.errors.append(msg)
                            passed = False
                        else:
                            self.warnings.append(msg)

                    # Check for URLs
                    if re.search(r'https?://', intent_args):
                        msg = f"Intent '{intent_name}' contains URL (move to #ref): {intent_args}"
                        if strict:
                            self.errors.append(msg)
                            passed = False
                        else:
                            self.warnings.append(msg)

                    # Check for long hex strings
                    if re.search(r'[a-fA-F0-9]{12,}', intent_args):
                        msg = f"Intent '{intent_name}' contains hex string (move to #ref): {intent_args}"
                        if strict:
                            self.errors.append(msg)
                            passed = False
                        else:
                            self.warnings.append(msg)

        return passed

    def validate_evidence(self) -> bool:
        """V2: Evidence records must have claim, src, conf."""
        passed = True
        for record in self.records:
            if record.startswith('#evid'):
                # Check for required fields
                has_claim = 'claim=' in record
                has_src = 'src=' in record
                has_conf = 'conf=' in record

                if not (has_claim and has_src and has_conf):
                    missing = []
                    if not has_claim:
                        missing.append('claim')
                    if not has_src:
                        missing.append('src')
                    if not has_conf:
                        missing.append('conf')
                    self.errors.append(f"#evid missing required fields: {', '.join(missing)}")
                    passed = False

        return passed

    def validate_refs(self) -> bool:
        """V3: All refs must match ref:<ns>:<type>:<id>."""
        passed = True
        ref_pattern = r'ref:\w+:\w+:\S+'

        for record in self.records:
            if record.startswith('#ref'):
                # Extract ref value
                ref_match = re.search(r'=\s*(ref:[^\s]+)', record)
                if ref_match:
                    ref_value = ref_match.group(1)
                    if not re.match(ref_pattern, ref_value):
                        self.errors.append(f"Invalid ref format: {ref_value}")
                        passed = False

        # Also check header refs
        for key, value in self.headers.items():
            if value.startswith('ref:'):
                if not re.match(ref_pattern, value):
                    self.errors.append(f"Invalid ref format in @{key}: {value}")
                    passed = False

        return passed

    def validate_rid_uniqueness(self) -> bool:
        """V6: All RIDs within a message must be unique."""
        passed = True
        rids = []

        for record in self.records:
            rid_match = re.search(r'@rid=(\w+)', record)
            if rid_match:
                rid = rid_match.group(1).lower()  # Canonical form is lowercase
                if rid in rids:
                    self.errors.append(f"Duplicate RID: {rid}")
                    passed = False
                else:
                    rids.append(rid)

        return passed

    def validate_budget(self, projected_cost: Optional[float] = None) -> Tuple[bool, str]:
        """V8: Budget compliance check."""
        if 'budget' not in self.headers:
            return True, "No budget specified"

        # Extract budget value (e.g., "0.05USD" -> 0.05)
        budget_str = self.headers['budget']
        budget_match = re.match(r'([\d.]+)([A-Z]+)', budget_str)
        if not budget_match:
            self.errors.append(f"Invalid budget format: {budget_str}")
            return False, "Invalid budget format"

        budget_value = float(budget_match.group(1))
        currency = budget_match.group(2)

        # If projected cost provided, check it
        if projected_cost is not None:
            if projected_cost > budget_value:
                msg = f"Projected cost {projected_cost} exceeds budget {budget_value} {currency}"
                self.warnings.append(msg)
                return False, msg

        # Check actual costs in message
        total_cost = 0.0
        for record in self.records:
            if record.startswith('#cost'):
                cost_match = re.search(r'val=([\d.]+)\s+cur=(\w+)', record)
                if cost_match:
                    cost_val = float(cost_match.group(1))
                    cost_cur = cost_match.group(2)
                    if cost_cur == currency:
                        total_cost += cost_val

        if total_cost > budget_value:
            msg = f"Total cost {total_cost} {currency} exceeds budget {budget_value} {currency}"
            self.errors.append(msg)
            return False, msg

        return True, f"Budget OK: {total_cost}/{budget_value} {currency} used"

    def validate(self, strict: bool = False) -> bool:
        """Run all validation rules."""
        if not self.validate_required_headers():
            return False

        self.validate_no_new_facts(strict)
        self.validate_evidence()
        self.validate_refs()
        self.validate_rid_uniqueness()
        self.validate_budget()

        return len(self.errors) == 0


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validator.py [--strict] <file.pairl>")
        sys.exit(1)

    strict = False
    filepath = sys.argv[1]

    if sys.argv[1] == '--strict':
        strict = True
        if len(sys.argv) < 3:
            print("Usage: python validator.py --strict <file.pairl>")
            sys.exit(1)
        filepath = sys.argv[2]

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    msg = PAIRLMessage(raw)

    print(f"Validating: {filepath}")
    print(f"Mode: {'strict' if strict else 'loose'}")
    print("-" * 50)

    # Parse errors
    if msg.errors:
        print(f"\n❌ Parse errors ({len(msg.errors)}):")
        for err in msg.errors:
            print(f"  - {err}")

    # Run validation
    valid = msg.validate(strict)

    # Validation errors
    if msg.errors:
        print(f"\n❌ Validation errors ({len(msg.errors)}):")
        for err in msg.errors:
            print(f"  - {err}")

    # Warnings
    if msg.warnings:
        print(f"\n⚠️  Warnings ({len(msg.warnings)}):")
        for warn in msg.warnings:
            print(f"  - {warn}")

    # Summary
    print(f"\n{'✓' if valid else '✗'} Validation {'PASSED' if valid else 'FAILED'}")

    # Message info
    print(f"\nMessage info:")
    print(f"  Version: {msg.headers.get('v', 'N/A')}")
    print(f"  ID: {msg.headers.get('mid', 'N/A')}")
    print(f"  Timestamp: {msg.headers.get('ts', 'N/A')}")
    print(f"  Records: {len(msg.records)}")

    if 'budget' in msg.headers:
        print(f"  Budget: {msg.headers['budget']}")

    sys.exit(0 if valid else 1)


if __name__ == '__main__':
    main()
