
```
 ______   ______     __    __     __
/\  == \ /\  __ \   /\ "-./  \   /\ \
\ \  _-/ \ \  __ \  \ \ \-./\ \  \ \ \____
 \ \_\    \ \_\ \_\  \ \_\ \ \_\  \ \_____\
  \/_/     \/_/\/_/   \/_/  \/_/   \/_____/

```

Paml is a Pythonic way to write HTML, featuring tight control over output,
minimal templating support (load, expand), and ability to convert to XML
and embeddable JavaScript.

Paml is a good replacement when writing long HTML pages, as the indentation
naturally ensures that tags are closed and structure is respected.

Projects like [HAML](#references) and [SLIP](#references) proved that a concise,
indentation-driven syntax can make authoring easier. Paml follows that path,
with a focus on:

- **Simplicity:** support inclusion/import without becoming a full template engine.
- **Fewer errors:** reduce common HTML mistakes (missing closes, unreadable nesting).
- **Single purpose:** generate HTML/XML well, without coupling to unrelated stacks.
- **Design + dev workflow:** useful both for prototyping and production markup.

## Quick Overview

Paml syntax is designed to be easy to learn, explicit, and consistent.

```text
<html
  <head
    <title:My first Paml document
  <body
    <h1:Lorem ipsum
    <p
      Lorem <b:ipsum dolor sit amet>, consectetuer adipiscing elit. Sed
      feugiat, dui eu condimentum porttitor, nisi erat ultrices elit, in
      sagittis sapien quam sed dolor.
```

Generated HTML:

```html
<html>
  <head>
    <title>My first Paml document</title>
  </head>
  <body>
    <h1>Lorem ipsum</h1>
    <p>
      Lorem <b>ipsum dolor sit amet</b>, consectetuer adipiscing elit. Sed
      feugiat, dui eu condimentum porttitor, nisi erat ultrices elit, in
      sagittis sapien quam sed dolor.
    </p>
  </body>
</html>
```

Key ideas:

- Paml is **indentation-driven**: indentation defines parent/child tags.
- Tags can be **inline** when convenient.

### Class and Id shorthands

You can use explicit attributes:

```text
<div(id=mydiv,class=classA classB)
```

Or the **shorthand syntax** for classes and identifiers:

```text
<div#mydiv.classA.classB
```

### Reusable blocks

For complex documents, define reusable blocks prefixed with `@` and inject them later:

```text
@head
  <title:My document
  <link(rel=Stylesheet,media=screen,type=text/css,href=screen.css)

@content
  <h1:Lorem ipsum
  <p:Dolor sit amet

<html
  <head=@head
  <body
    <div=@content
```

### Embedded Content

Paml can embed **typed content blocks** that can be post-processed:

```text
@style:[css|
  html, body {
    margin: 0;
    padding: 0;
  }
  #toolbar ul {
    list-style-type: none;
  }
]
```

The `[type| ... ]` block lets processors handle content according to language.

### File includes

Include a sibling file:

```text
%include library
```

If not found locally, Paml can look in `PAML_LIBRARY` (colon-separated paths).

Include nested library files:

```text
%include widget/datepicker
```

Pass replacement values for `${VARIABLE}` placeholders:

```text
%include widget/datepicker {ID=mywidget,TITLE="Start date"}
```

Example snippet:

```text
<div#${ID}.DatePicker
  <h3.title:${TITLE}
```

Add/override class and attributes on import:

```text
%include widget/datepicker +.Imported(date=2009-10-23)
```

### Tight HTML output control

Paml supported **rendering hints** indicating how to post-process
the node, appended with `|` after tag/id/class/attributes:

```text
<span|s
<div#mydiv.myClass(attr=value)|s
```

Supported hints:

- `sl` (single-line): render content on one line.
- `i` (inline): inline output when content has no newline.
- `w` (wrap, default): wrap text to configured width (default: 80).
- `p` (preserve): preserve text as-is (useful for `pre`, `code`).
- `n` (normalize): convert tabs/newlines to spaces, collapse repeated spaces.
- `s` (strip): trim leading/trailing spaces.
- `c` (compact): avoid extra whitespace around opening/closing tag.

You can also define hint defaults for element groups:

```text
@pre,code|p
```

This sets default format hints for the named elements. The `@` declaration without `<>` sets defaults for those element names.

## API

Paml can also be used as a Python library to parse Paml text and convert it
to different output formats.

### Quick start

```python
import paml

source = """
<html
  <body
    <h1:Hello
"""

html = paml.toHTML(source)              # same as paml.process(source)
xml  = paml.process(source, format="xml")
js   = paml.process(source, format="js")
```

Available formats:

- `"html"` (default)
- `"xhtml"` (strict/self-closing style where appropriate)
- `"xml"`
- `"js"` (JavaScript `html.tag(...)` builder output)

### Parse from string

```python
import paml

result = paml.process("<p:Hello from Paml", format="html")
```

The `path` argument is optional and useful when resolving `%include` paths:

```python
result = paml.process(source_text, path="templates/page.paml", format="html")
```

### Parse from file

```python
from paml.engine import Parser, formatter

parser = Parser(formatter=formatter("html"))
html = parser.parseFile("templates/page.paml")
```

### Advanced usage with explicit formatters

```python
from paml.engine import Parser, HTMLFormatter, XMLFormatter, JSFormatter

html_parser = Parser(formatter=HTMLFormatter(strict=False))
xhtml_parser = Parser(formatter=HTMLFormatter(strict=True))
xml_parser = Parser(formatter=XMLFormatter())
js_parser = Parser(formatter=JSFormatter())
```

### Notes

- `paml.toHTML` and `paml.process` are aliases of `paml.engine.parse`.
- `paml.engine.parse(text, path=None, format="html")` is the core API.
- JS output is designed for `html.js`-style rendering and expects a single
  root element.

## CLI

Paml ships with two command-line tools: `paml` and `html2paml`.

### `paml` (Paml -> HTML/XML/JS)

```bash
paml [-t html|xhtml|xml|js] [-f html|htm|xhtml|xml] [-d KEY=VALUE] [file]
```

- If `file` is omitted, input is read from stdin.
- `-t, --to` selects the output format (default is `html`).
- `-f, --from` converts HTML/XML input back to Paml.
- When `-f` is omitted, `paml` auto-detects `.html`, `.htm`, `.xhtml`, and `.xml` input files.
- `-d, --def KEY=VALUE` defines variables used by include substitutions.

Examples:

```bash
# Convert file to HTML (default)
paml page.paml

# Convert to XML
paml -t xml page.paml

# Convert stdin to XHTML
cat page.paml | paml -t xhtml

# Convert HTML to Paml
paml -f html input.html

# Pass variables used by ${...} placeholders in includes
paml -d ID=mywidget -d TITLE="Start date" page.paml
```

### `html2paml` (HTML -> Paml)

```bash
html2paml input.html
```

This parses an HTML file and prints the corresponding Paml to stdout.

# Quick Reference

## Basic Element Syntax

| Element | Syntax | HTML |
| --- | --- | --- |
| Inlined element | `<tag:...>` | `<tag>...</tag>` |
| Block element | `<tag` + indented content | `<tag>...</tag>` |
| Attributes | `<a(href=http://...):link` | `<a href="http://...">link</a>` |

Example:

```text
Lorem <span:ipsum dolor> sit <a(href=http://www.google.com):amet>
```

## ID and Class Syntax

| Element | Syntax | HTML |
| --- | --- | --- |
| Element ID | `<tag#myid:...>` | `<tag id="myid">...</tag>` |
| Element class | `<span.mySpanClass:...>` | `<span class="mySpanClass">...</span>` |

## Declaration and Inclusion

| Element | Syntax |
| --- | --- |
| Element declaration | `@element` |
| Element reference | `<div=@element` |

## Language Declarations

| Element | Syntax |
| --- | --- |
| CSS declaration | `<div:[css|...]` |
| JavaScript declaration | `<script:[javascript|...]` |
| TypeScript declaration | `<script:[typescript|...]` |
| CoffeeScript declaration | `<script:[coffee|...]` |

See [Embedded Language Processors](#embedded-language-processors) for full list.

## Macros

Macros are prefixed with `%` and provide powerful import and dependency management:

```text
%require:css(select,button)
%require:js(jquery,myapp)
%import:js(module-a,module-b)
```

### Macro types

| Macro | Description |
| --- | --- |
| `%require:css(...)` | Looks for CSS files in `src/css`, `lib/css`, etc. and generates `<link>` tags |
| `%require:js(...)` | Looks for JS files and generates `<script>` tags |
| `%require:gmodule(...)` | Google Closure module imports with dependency resolution |
| `%import:js(...)` | ES6-style imports with recursive dependency resolution |

### Search paths for require macros

Files are looked up in order:
- `src/pcss/`, `src/ccss/`, `src/css/`, `lib/pcss/`, `lib/ccss/`, `lib/css/`
- `src/sjs/`, `src/ts/`, `src/js/`, `lib/sjs/`, `lib/ts/`, `lib/js/`

Versioned files (e.g., `select-0.7.9.js`) are automatically picked if available.

## Embedded Language Processors

Paml supports embedded content blocks with language processors:

```text
<div:[typescript|
  export function greet(name: string): string {
    return `Hello, ${name}`;
  }
]
```

### Supported languages

| Language | Syntax | Notes |
| --- | --- | --- |
| CSS | `[css\|...]` | Embedded stylesheets |
| JavaScript | `[javascript\|...]` | Embedded scripts |
| TypeScript | `[typescript\|...]` or `[ts\|...]` | Requires `tsc` CLI |
| CoffeeScript | `[coffeescript\|...]` or `[coffee\|...]` | Requires `coffee` CLI |
| CleverCSS | `[clevercss\|...]` or `[ccss\|...]` | Python library |
| PythonicCSS | `[pythoniccss\|...]` or `[pcss\|...]` | Requires `pcss` CLI |
| Nobrackets | `[lang+nobrackets\|...]` | Various prefix options |
| Texto | `[texto\|...]` | TextOb format |
| HJSON | `[hjson\|...]` | JSON serialization |
| Raw | `[raw\|...]` | Unprocessed content |
| Sugar | `[sugar1\|...]` | Sugar parser |
| Raw + Escape | `[raw+escape\|...]` | HTML-escaped raw content |

## Comments and Special Elements

### Regular comments

```text
# This is a comment (not rendered)

#START:MYBLOCK
<div content here>
#END:MYBLOCK
```

### XML-style elements

```text
<!-- This is an XML comment -->

<?xml-stylesheet type="text/xsl" href="style.xsl"?>

<!DOCTYPE html>
```

### SVG Sprites

Reference SVG symbols with `%use`:

```text
%use #icon-arrow
%use #icon-arrow.myClass
%use #icon-arrow 24x24
```

## Format Hints

Additional hints not covered in the Tight HTML output section:

| Hint | Name | Description |
| --- | --- | --- |
| `ib` | inline-block | Inline block output |
| `x` | XSL escape | Apply XSL escaping |

## Formatters

Paml provides multiple output formatters:

```python
from paml.engine import Parser, HTMLFormatter, XMLFormatter, JSFormatter

html_parser = Parser(formatter=HTMLFormatter(strict=False))  # Default HTML5
xhtml_parser = Parser(formatter=HTMLFormatter(strict=True))  # Self-closing tags
xml_parser = Parser(formatter=XMLFormatter())               # XML output
js_parser = Parser(formatter=JSFormatter())                 # JavaScript builder
```

### HTMLFormatter options

- `strict=True/False` - When `True`, uses self-closing syntax (`<br />`) for void elements

## Web Components

Paml supports web components and custom elements by outputting explicit open/close tags for element names containing hyphens. This ensures compatibility with the Custom Elements specification.

```text
<ui-icon#my-icon(name=value)
<custom-button[type=primary]:Click me
<my-element
  <span:Content
```

Outputs:

```html
<ui-icon id="my-icon" name="value"></ui-icon>
<custom-button type="primary">Click me</custom-button>
<my-element><span>Content</span></my-element>
```

Empty elements with hyphens in names use `<ui-icon></ui-icon>` instead of `<ui-icon />` to comply with the HTML parsing specification.

## References

- **HAML:** markup haiku, <http://haml.hamptoncatlin.com/tutorial>
- **SLIP:** a "Sorta Like Python" shorthand for XML, <http://slip.sourceforge.net/>
- **YAML:** Yet Another Markup Language, <http://www.yaml.org>
