# ADR 0002 — English-first development and internationalization

Status: accepted for future development.

## Context
The project is open source and should support international contributors while remaining accessible to Brazilian users.

## Decision
- Use English for identifiers, comments, docstrings, technical documentation, commits, issues and pull requests.
- Keep English as the source language for user-facing strings; provide Brazilian Portuguese as the first translation.
- Use Qt translation facilities (QCoreApplication.translate or QObject.tr, QTranslator, TS catalogs and compiled QM resources).
- Keep translations out of domain logic. Use stable machine-state identifiers and localize their display labels only.
- Never localize G-code, serial protocol fields, JSON numeric values or machine units. Localized numeric input must be explicitly parsed and validated before conversion to canonical values.
- Maintain an English README and a Brazilian Portuguese companion README.
- Engineering discussions may remain in Portuguese.

## Validation
Test English fallback, Portuguese catalog loading, missing translations, placeholders and locale-independent G-code formatting. Translation catalogs and GUI tests are planned, not yet implemented.

## Consequences
New contributions follow this policy; existing Portuguese technical documents and UI strings will be migrated incrementally. Additional languages can be contributed independently.
