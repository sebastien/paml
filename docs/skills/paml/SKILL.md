---
name: paml
description: Use when writing, editing, reviewing, or converting Paml templates or when changing the Paml parser, formatter, includes, macros, or embedded-language behavior in this repository.
---

# Paml

Use this skill when the task involves:

- Authoring or editing `.paml` files
- Explaining Paml syntax or behavior
- Updating the parser or formatter in `src/py/paml/engine.py`
- Working on `%include`, `%use`, `%require:*`, `%import:*`, or embedded `@mode`
- Verifying rendered HTML, XML, XHTML, or JS output from Paml

## Workflow

1. Read the local syntax reference first: `docs/ref-paml.md`.
2. If exact behavior matters, verify it in `src/py/paml/engine.py` instead of
   guessing from memory.
3. Check `tests/*.paml` for repo-native examples before inventing new syntax.
4. If you change parser behavior, validate with the CLI on targeted fixtures.
5. Preserve existing Paml style in the file you edit unless the task explicitly
   asks for cleanup or normalization.

## Source Map

Read these files depending on the task:

- `docs/ref-paml.md`: implementation-grounded language reference
- `README.md`: higher-level overview, API, and CLI usage
- `src/py/paml/engine.py`: parser, formatter, includes, macros, embeds
- `src/py/paml/importer.py`: HTML/XML to Paml conversion logic
- `tests/*.paml`: syntax fixtures and regression coverage
- `etc/paml.vim`: useful shorthand view of recognized syntax forms

## Authoring Rules

- Use indentation to express nesting. Do not add closing tags manually.
- Prefer the repo’s native shorthand: `<tag`, `<tag:...`, `#id`, `.class`,
  `(attr=value,...)`.
- Keep attribute lists comma-separated.
- Use `::` in source when the output name or attribute needs a namespace `:`.
- Use `@name` declarations and `=@name` reuse when repeating structured blocks.
- Use `%include` for shared fragments instead of copy-pasting markup.
- Use embedded modes only when the content should not be parsed as Paml.

## Important Behaviors

Do not assume generic Haml-like behavior. This implementation has specific
rules that matter:

- Inline content is introduced by `:`
- Embedded content mode is introduced by `@mode`
- Includes support substitutions: `%include path {NAME=value}`
- Includes support first-element overrides: `%include path +.class(attr=value)`
- `%use` emits an inline SVG wrapper with a nested `<use>`
- Web components with `-` in the tag name render with explicit open/close tags
- Parser behavior should be treated as authoritative when docs and intuition
  diverge

## Verification

Use the local CLI to verify output from real files:

```bash
PYTHONPATH=src/py python3 bin/paml path/to/file.paml
PYTHONPATH=src/py python3 bin/paml -t xml path/to/file.paml
PYTHONPATH=src/py python3 bin/paml -t xhtml path/to/file.paml
```

Useful validation patterns:

- Render the edited fixture and inspect the exact output
- Compare behavior with nearby files in `tests/`
- When changing parser logic, run a few focused fixtures that exercise the
  same construct

## Editing Guidance

When editing `.paml`:

- Keep line-oriented structure simple and readable
- Prefer declarations/includes over duplicated blocks
- Avoid introducing syntax that is not already supported by the parser
- If markup must preserve whitespace, use the relevant formatting hint or
  existing element convention instead of relying on incidental formatting

When editing the parser or formatter:

- Make the smallest coherent change in `src/py/paml/engine.py`
- Check whether the behavior is covered by an existing fixture before adding
  a new one
- Add or update a focused `.paml` fixture when fixing a regression
- Verify both parsing and rendered output, not just parser acceptance

## Review Focus

When reviewing Paml-related changes, prioritize:

- Syntax that looks plausible but is not actually supported
- Include or substitution behavior changes
- Whitespace and inline/block rendering regressions
- Namespace handling and custom-element serialization
- Embedded-mode changes that accidentally parse raw content as Paml
- Missing regression fixtures for parser or formatter changes
