# Paml Reference

This document is a language reference for Paml as implemented in this repository.
It describes the syntax accepted by the current parser and highlights behaviors
that are easy to miss when reading examples alone.

## Overview

Paml is an indentation-based shorthand for writing HTML and XML-like documents.
It reduces closing-tag noise while staying close to the target markup.

Core rules:

- Lines starting with `<` declare elements.
- Indentation defines parent/child structure.
- `:` starts inline content on the same line.
- `#id`, `.class`, and `(attr=value,...)` extend element declarations.
- `%...` introduces includes and macros.
- `@name` declares reusable blocks.

## Indentation

Indentation determines nesting.

```paml
<html
    <body
        <h1:Hello
        <p
            Welcome
```

Mixed indentation is accepted by default. Parser helpers exist for tabs-only or
spaces-only modes, but the CLI uses the default permissive parser.

## Elements

### Block elements

A line beginning with `<name` opens an element. Child content is provided by
more-indented lines.

```paml
<ul
    <li:One
    <li:Two
```

### Inline elements

Add `:` to put content on the same line.

```paml
<title:My page
<a(href=/about):About
```

Inline elements can also appear inside text:

```paml
Read the <a(href=/docs):documentation> first.
```

### Empty elements

An empty declaration still produces an element. In HTML mode, built-in void
elements such as `meta`, `img`, and `br` are emitted without closing tags.

Custom elements containing `-` are never self-closed in HTML mode:

```paml
<ui-icon(name=search)
```

renders as:

```html
<ui-icon name="search"></ui-icon>
```

### Namespaced elements

Use `::` in Paml source to emit `:` in the output name or attribute name.

```paml
<fb::like
<html(xmlns::og="http://ogp.me/ns#")
```

renders as `fb:like` and `xmlns:og`.

## IDs, classes, and attributes

### ID shorthand

```paml
<div#main
```

### Class shorthand

```paml
<div.panel.primary
```

Multiple classes become a space-separated `class` attribute.

### Combined shorthand

```paml
<div#main.panel.primary
```

### Attribute list

Attributes use parentheses with comma-separated entries:

```paml
<input(type=text,value=Search)
<meta(http-equiv="x-ua-compatible",content="IE=8")
```

Rules:

- Attribute separators are commas, not spaces.
- Values may be unquoted, single-quoted, or double-quoted.
- `name` without `=value` is accepted and becomes an attribute with no value.
- Attribute names also support `::` for namespaces.

If shorthand classes and an explicit `class=...` attribute are both present,
Paml prepends the shorthand classes to the explicit ones.

## Text content

Plain lines that do not start with a recognized construct become text content
of the current element.

```paml
<p
    This is plain text.
    So is this.
```

Inline elements can be mixed with text on the same line.

```paml
<p
    Click <b:Save> to continue.
```

Literal `<` and `>` in text are escaped by the formatter.

## Declarations and reuse

Declarations define reusable content blocks. A declaration begins with `@name`
at line start and captures its indented body.

```paml
@head
    <title:My page
    <meta(charset=utf-8)

<html
    <head=@head
```

Element reuse is attached with `=@name` on an element declaration:

```paml
<div=@content
```

This injects the declared content inside the element.

### Default format declarations

Declarations can also set default formatting hints for element names:

```paml
@pre,code|p
```

This applies the `p` hint to future `pre` and `code` elements.

## Includes

`%include` inserts another file at parse time.

```paml
%include widget/card
%include "widget/card"
```

Resolution order:

- Relative to the current file stack.
- Relative to the current parser path.
- Then through search paths including `PAML_LIBRARY`.

If the target path has no extension, `.paml` is tried automatically.

### Include substitutions

You can substitute `${NAME}` placeholders while including:

```paml
%include widget/card {TITLE=Hello,ID=hero}
```

Included Paml:

```paml
<div#${ID}
    <h2:${TITLE}
```

### Include overrides

You can override the attributes of the first element emitted by the included
file by appending `+...` syntax:

```paml
%include widget/card +.featured(data-kind=promo)
```

This is parsed like extra shorthand on a synthetic `div`, so both class and
attribute overrides are supported.

### Non-Paml includes

If the included file is not a `.paml` file, it is inserted as raw text.

## Comments and special nodes

### Paml comments

Lines beginning with `#` are comments and are not rendered:

```paml
# This is ignored
```

Special block markers such as `#START:...` and `#END:...` become comment nodes
only when not inside an embedded block.

### XML comments

XML/HTML comments are preserved:

```paml
<!-- visible in output -->
```

### Processing instructions

Processing instructions are preserved:

```paml
<?xml version="1.0" encoding="UTF-8"?>
<?php echo "hello"; ?>
```

Indented content under a processing-instruction line is treated as its body
where the target formatter supports it.

### Doctype

Doctypes are preserved:

```paml
<!DOCTYPE html>
```

## Embedded content modes

Elements can switch their body into a raw embedded mode by appending `@mode`
to the element declaration:

```paml
<style(type=text/css)@css
    body { margin: 0; }

<script@typescript
    export const answer: number = 42
```

In embedded mode, the indented body is not parsed as Paml. It is collected as
source text and optionally post-processed by the formatter.

Supported modes in the current implementation include:

- `raw`
- `raw+escape`
- `css`
- `javascript`
- `typescript`, `ts`
- `coffeescript`, `coffee`
- `clevercss`, `ccss`
- `pythoniccss`, `pcss`
- `texto`
- `hjson`
- `sugar...` such as `sugar` or `sugar1`

Some modes require external tools such as `tsc` or `coffee` to be installed.

## Macros

Macros use `%name(...)` syntax or `%name:subname(...)` syntax.

```paml
%require:css(select,button)
%require:js(app)
%require:gmodule(foo.bar.Baz)
%import:js(module-a,module-b)
```

The built-in macro catalogue currently includes:

- `%require:css(...)`
- `%require:js(...)`
- `%require:gmodule(...)`
- `%import:js(...)`

These expand into generated tags or inline script content based on files found
in source and library search paths.

### `%require:css(...)`

Looks up CSS-like assets and emits `<link>` elements.

### `%require:js(...)`

Looks up JavaScript-like assets and emits `<script src=...>` elements.

### `%require:gmodule(...)`

Resolves Google Closure-style modules and emits dependency-aware script tags.

### `%import:js(...)`

Builds a raw `<script>` block containing import statements gathered from the
requested modules and their dependencies.

## SVG symbol use

`%use` expands to an inline SVG `<use>` reference:

```paml
%use #icon-arrow
%use #icon-arrow.large
%use #icon-arrow 24x24
```

The supported syntax is:

- `#id`
- optional `.class`
- optional `WIDTHxHEIGHT`

It renders an `<svg>` wrapper with a nested `<use xlink:href="#...">`.

## Formatting hints

Hints are appended with `|` on an element declaration and combined with `+`.

```paml
<span|s
<p|n+c
<pre|p
```

Supported hints in the parser:

| Hint | Meaning |
| --- | --- |
| `i` | Inline formatting |
| `ib` | Inline-block formatting |
| `sl` | Single-line formatting |
| `p` | Preserve whitespace |
| `x` | XSL-oriented escaping |
| `n` | Normalize whitespace |
| `s` | Strip leading and trailing whitespace |
| `c` | Compact surrounding whitespace |

Notes:

- `sl` also implies normalized text handling.
- `w` exists in the formatter and is used by defaults, but it is not accepted by
  the current element-hint parser because hints are restricted to single-letter
  forms in source syntax.
- Some defaults are applied automatically by the HTML formatter.

### HTML formatter defaults

Current built-in defaults include:

- `script` -> `p`
- `link` -> `i`
- `title`, `h1`, `h2`, `h3`, `h4` -> `sl n`
- `p` -> `n c w`
- `code`, `pre` -> `p`
- `div` -> `ib`

## BEM shorthand

The test suite includes a BEM-oriented convention where classes beginning or
ending with `-` are expanded relative to ancestor block names.

Example:

```paml
<div.widget-.A
    <ul.-list.-list-.B
        <li.-element.C:1
```

This renders classes such as `widget-list` and `widget-list-element`.

This behavior is implementation-specific rather than standard HTML shorthand,
so treat it as a Paml extension.

## Output formats

The parser can render to:

- `html`
- `xhtml`
- `xml`
- `js`

`html` is the default. `xhtml` uses stricter empty-element serialization.
`xml` preserves XML-oriented forms. `js` emits an `html.tag(...)`-style builder
representation and expects a single root node.

## CLI

The main CLI is:

```bash
paml [-t html|xhtml|xml|js] [-d KEY=VALUE] [file]
```

Notes:

- If `file` is omitted, input is read from stdin.
- `-d` defines default substitution variables used by includes.
- `html2paml input.html` converts HTML back to Paml.

## Grammar summary

The practical element grammar is:

```text
<name[#id][.class...][(attr=value,...)][|hint[+hint...]][@mode][:]
```

Where:

- `name` may contain letters, digits, `_`, `-`, and namespace `::`.
- `#id` is optional.
- `.class` may repeat.
- `(attrs)` is optional.
- `|...` is optional.
- `@mode` is optional.
- trailing `:` enables same-line content.

## Implementation notes

These details reflect current behavior in `src/py/paml/engine.py`:

- Include substitution starts with parser defaults, then applies explicit
  `{NAME=value}` pairs.
- Missing include files render an inline error message instead of raising a hard
  parse failure.
- Attribute lists must be comma-separated; whitespace-separated attributes are
  not supported.
- The parser recognizes inline elements by finding a closing `>` before another
  opening `<` on the same line.
- Web components and several specific elements are forced to use explicit
  closing tags in HTML mode.

## Minimal examples

### Simple page

```paml
<!DOCTYPE html>
<html
    <head
        <title:Hello
    <body
        <h1:Hello
        <p
            Welcome to <b:Paml>.
```

### Reuse plus include

```paml
@hero
    <h1:Product
    <p:Fast, simple markup.

<html
    <body
        <section=@hero
        %include "partials/footer"
```

### Embedded stylesheet

```paml
<style(type=text/css)@css
    body {
        margin: 0;
    }
```
