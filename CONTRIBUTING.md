# Contributing to PAIRL

Thank you for your interest in contributing to PAIRL! This document provides guidelines for contributing to the specification, reference implementations, and documentation.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How Can I Contribute?](#how-can-i-contribute)
3. [Specification Changes](#specification-changes)
4. [Implementation Contributions](#implementation-contributions)
5. [Documentation](#documentation)
6. [Style Guidelines](#style-guidelines)
7. [Versioning Policy](#versioning-policy)

---

## Code of Conduct

This project follows a simple principle: **Be respectful and constructive**.

* Focus on technical merit and use cases
* Assume good faith in discussions
* Critique ideas, not people
* Welcome newcomers and answer questions patiently

---

## How Can I Contribute?

### 1. Reporting Issues

**Specification Issues**:
* Ambiguous wording
* Missing edge cases
* Inconsistencies between sections
* Unclear examples

**Implementation Issues**:
* Bugs in reference parsers/validators
* Performance problems
* Compatibility issues

**How to Report**:
* Use GitHub Issues
* Include PAIRL version (e.g., v1.1)
* Provide minimal reproducible example
* Tag appropriately: `spec`, `implementation`, `docs`, `question`

### 2. Proposing New Features

Before proposing a new feature:

1. **Check existing issues** — someone may have already proposed it
2. **Read the design principles** (§0 in SPEC.md)
3. **Consider backward compatibility** — can it be added without breaking v1.x?

**Feature Proposals Should Include**:
* **Use case**: What problem does this solve?
* **Example**: Show the proposed syntax
* **Alternatives considered**: Why is this better than other approaches?
* **Breaking changes**: Does this require a major version bump?

### 3. Contributing Code

See [Implementation Contributions](#implementation-contributions) below.

---

## Specification Changes

### Process for Spec Changes

1. **Open an Issue** — Describe the proposed change and rationale
2. **Discuss** — Gather feedback from maintainers and community
3. **Draft PR** — Update SPEC.md with proposed changes
4. **Update CHANGELOG** — Add entry to CHANGELOG.md
5. **Review** — Maintainers review for consistency and impact
6. **Merge** — Once approved, changes are merged

### What Requires a Spec Change?

**Minor version bump** (backward compatible):
* New intent types (e.g., `bid`, `ref` in v1.1)
* New optional record types (e.g., `#cost`, `#quota`)
* New optional headers (e.g., `@budget`)
* Clarifications/examples that don't change behavior

**Major version bump** (breaking changes):
* Changes to required headers
* Changes to canonicalization rules
* Removal of record types
* Changes to validation rules (if required, not optional)

### Spec Style Guide

* **Be concise**: Favor clarity over verbosity
* **Use examples**: Show, don't just tell
* **Link between sections**: Use `§` notation (e.g., "see §7.3")
* **Maintain structure**: Follow existing numbering/formatting

---

## Implementation Contributions

### Reference Implementations

We welcome reference implementations in any language. Priority languages:

* **Python** — for data science / LLM pipelines
* **TypeScript** — for web/Node.js environments
* **Rust** — for high-performance / embedded use cases

### Implementation Guidelines

**Core Features** (must-have):
* Parser (headers + records)
* Validator (V1-V8 rules, configurable strict/loose)
* Canonicalizer (for hashing/diffing)
* Basic ref resolver (extensible)

**Optional Features** (nice-to-have):
* Renderer (PAIRL → natural language)
* Budget tracker (for v1.1 economic features)
* CLI tool (validate, canonicalize, render)
* Streaming parser (for large messages)

### Code Standards

* **Testing**: Aim for >80% coverage
* **Examples**: Include at least 5 test cases from examples/
* **Documentation**: README with usage examples
* **License**: Apache 2.0 (match project license)

### Where to Submit

* Create `implementations/<language>/` directory
* Include README, tests, and examples
* Add entry to main README's "Implementations" section

---

## Documentation

### What Needs Documentation?

* **Spec changes**: Always update SPEC.md + CHANGELOG.md
* **New features**: Add to appropriate section, include examples
* **Use cases**: Add to README.md "Use Cases" if business-relevant
* **Examples**: Add to examples/ directory

### Documentation Style

* **Clear headings**: Use descriptive section titles
* **Code blocks**: Always specify language (```pairl, ```python, etc.)
* **Internal links**: Link to relevant sections
* **Versioning**: Mark version-specific features (e.g., "v1.1")

---

## Style Guidelines

### PAIRL Message Style

When contributing examples:

**DO**:
```
@v 1
@mid ref:msg:01JH0Q6Z7F8K4Q2S1R6E2E9A3B
@ts 2026-01-31T16:20:01.123+01:00

req{t=task,s=f,l=2,m=+} @rid=a1
#fact id=123 @rid=f1
#ref doc=ref:doc:sha256:abc... @rid=r1
```

**DON'T**:
```
@v 1
req{t=task} # Missing required headers @mid, @ts
#fact id = 123  # Extra spaces around =
#ref doc = "ref:doc:sha256:abc..." # Quoted ref (should be unquoted)
```

### Intent Registry Additions

When proposing new intents:

* **Length**: 2-4 characters, lowercase
* **Namespace**: Use `org.name.intent` for custom intents
* **Documentation**: Include description + example

**Template**:
```markdown
* `xyz` — description of what this intent does
   * Example: `xyz{t=topic,s=f,l=1} #fact key=value`
```

---

## Versioning Policy

PAIRL follows [Semantic Versioning](https://semver.org/):

* **MAJOR** (v2.0): Breaking changes (incompatible with v1.x parsers)
* **MINOR** (v1.2): New features, backward compatible
* **PATCH** (v1.1.1): Bug fixes, clarifications

### What Counts as Breaking?

**Breaking changes** (require major version bump):
* Removing required headers
* Changing canonicalization rules
* Making optional features required
* Renaming core intent types

**Non-breaking changes** (minor version bump):
* Adding optional headers/records
* New intent types
* Clarifications to spec text
* Additional examples

---

## Review Process

### Timeline

* **Small changes** (typos, examples): 2-3 days
* **Medium changes** (new intents, clarifications): 1 week
* **Large changes** (new record types, validation rules): 2-4 weeks

### Approval Requirements

* **Spec changes**: 2 maintainer approvals
* **Implementation PRs**: 1 maintainer approval + CI passing
* **Documentation**: 1 maintainer approval

---

## Getting Help

**Questions about the spec?**
* Open a GitHub Issue with `question` tag
* Read SPEC.md §0-4 for design principles

**Implementation help?**
* Check examples/ directory
* Look at existing implementations (if available)
* Ask in GitHub Discussions

**Want to join as a maintainer?**
* Contribute 3+ meaningful PRs
* Demonstrate understanding of spec design principles
* Reach out to existing maintainers

---

## Recognition

Contributors are recognized in:

* GitHub contributor list (automatic)
* CHANGELOG.md (for significant contributions)
* Main README (for reference implementations)

---

## License

By contributing to PAIRL, you agree that your contributions will be licensed under the Apache License 2.0.

---

Thank you for helping improve PAIRL!
