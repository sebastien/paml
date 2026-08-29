# Module: paml
# Public package API for parsing, rendering, and importing Paml documents.

from paml.cli import parse as parse, run as run
from paml.parser import PamlParser as PamlParser
from paml.formatter import HTMLFormatter as HTMLFormatter, JSFormatter as JSFormatter, XMLFormatter as XMLFormatter, createFormatter as createFormatter, formatter as formatter
from paml.writer import PamlWriter as PamlWriter
from paml.model import PamlComment as PamlComment, PamlElement as PamlElement, PamlText as PamlText, PamlRawText as PamlRawText, PamlDeclaration as PamlDeclaration, XMLComment as XMLComment, DocType as DocType, ProcessingInstruction as ProcessingInstruction
from paml.macros import PamlMacro as PamlMacro
from paml.version import __version__ as __version__, PAMELA_VERSION as PAMELA_VERSION

# Legacy aliases (backward compat)
toHTML = process = parse

__all__ = (
	"parse",
	"run",
	"PamlParser",
	"PamlWriter",
	"PamlElement",
	"PamlText",
	"PamlRawText",
	"PamlComment",
	"PamlDeclaration",
	"XMLComment",
	"DocType",
	"ProcessingInstruction",
	"HTMLFormatter",
	"JSFormatter",
	"XMLFormatter",
	"formatter",
	"createFormatter",
	"PamlMacro",
	"__version__",
	"PAMELA_VERSION",
	"toHTML",
	"process",
)

# EOF
