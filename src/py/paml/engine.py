# -----------------------------------------------------------------------------
# Project           :   PAML — engine backward-compat shim
# -----------------------------------------------------------------------------
# The engine module has been split into domain-specific submodules.
# This file re-exports everything under canonical names so that
# existing code (bin/paml, setup.py, third-party imports) continues to
# work without changes.
# -----------------------------------------------------------------------------

import re
import warnings

from paml.cli import parse as parse, run as run
from paml.formatter import HTMLFormatter as HTMLFormatter, JSFormatter as JSFormatter, XMLFormatter as XMLFormatter, createFormatter as createFormatter, formatter as formatter
from paml.macros import PamlMacro as PamlMacro
from paml.model import PamlComment as PamlComment, PamlDeclaration as PamlDeclaration, PamlElement as PamlElement, PamlRawText as PamlRawText, PamlText as PamlText, ProcessingInstruction as ProcessingInstruction, XMLComment as XMLComment, DocType as DocType
from paml.parser import PamlParser as Parser
from paml.version import PAMELA_VERSION as PAMELA_VERSION, __version__ as __version__
from paml.writer import PamlWriter as PamlWriter

PamlParser = Parser
toHTML = process = parse
warnings.warn(
	"paml.engine is deprecated; import directly from paml or its submodules",
	DeprecationWarning,
	stacklevel=2,
)

# Version

# Utilities

# Grammar

# Model

# Writer

# Macros

# Parser

# Formatter
RE_SPACES = re.compile(r"\s")

# Keep the module directly runnable
if __name__ == "__main__":
	from paml.cli import run
	import sys
	sys.stdout.write(run(sys.argv[1:]))

# EOF
