from paml.cli import parse as parse, run as run
from paml.parser import PamlParser as PamlParser
from paml.formatter import HTMLFormatter as HTMLFormatter, JSFormatter as JSFormatter, XMLFormatter as XMLFormatter, formatter as formatter
from paml.writer import PamlWriter as PamlWriter
from paml.model import PamlElement as PamlElement, PamlText as PamlText, PamlRawText as PamlRawText, PamlDeclaration as PamlDeclaration, XMLComment as XMLComment, DocType as DocType, ProcessingInstruction as ProcessingInstruction
from paml.macros import PamlMacro as PamlMacro
from paml.version import __version__ as __version__, PAMELA_VERSION as PAMELA_VERSION

# Legacy aliases (backward compat)
toHTML = process = parse
