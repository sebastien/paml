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
