# Contributing

## Project Rules

- Version bumps are semantic:
  - patch: fixes, compatibility, diagnostics, documentation, testing
  - minor: new entities, services, or user-visible capabilities without breaking config
  - major: breaking config or behavior changes
- Commit messages must follow repository rules:
  - single-line: `add:`, `change:`, `deprecate:`, `remove:`, or `fix:`
  - multi-line: short summary, blank line, then categorized body lines
- Release notes must contain these headings in this order:
  - `### New Features`
  - `### Improvements`
  - `### Changes`
  - `### Bugfixes`

## Home Assistant Direction

This repository aims to stay close to Home Assistant integration conventions:

- config flow first
- diagnostics available for supportability
- entity creation only when data is actually present
- tests for runtime logic and Home Assistant imports
- branding, translations, and metadata kept consistent
