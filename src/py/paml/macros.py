# Module: macros
# Built-in resource and module macros used during Paml parsing.

import os
import json
import glob
import types
from functools import reduce

from paml.utils import flatten
from paml.grammar import TAB_WIDTH

try:
	import deparse
except ImportError:
	deparse = None

# -----------------------------------------------------------------------------
#
# MACRO
#
# -----------------------------------------------------------------------------


class PamlMacro:
	"""A collection of macros used by the parser. The `CATALOGUE` can
	be updated live to register more macros."""

	CSS_PATTERNS = (
		"src/pcss/{0}.pcss",
		"src/ccss/{0}.ccss",
		"src/css/{0}.css",
		"src/css/{0}-*.css",
		"lib/pcss/{0}.pcss",
		"lib/ccss/{0}.ccss",
		"lib/css/{0}.css",
		"lib/css/{0}-*.css",
	)

	JS_PATTERNS = (
		"src/sjs/{0}.sjs",
		"src/ts/{0}.ts",
		"src/js/{0}.js",
		"src/js/{0}-*.js",
		"lib/sjs/{0}.sjs",
		"lib/ts/{0}.ts",
		"lib/js/{0}.js",
		"lib/js/{0}-*.js",
	)

	GMODULE_PATTERNS = (
		"lib/sjs/{0}.sjs",
		"lib/js/{0}.gmodule.js",
		"lib/js/{0}-*.gmodule.js",
	)

	@classmethod
	def Get(cls, name):
		return cls.CATALOGUE.get(name)

	@classmethod
	def IndentAsString(cls, indent):
		return (
			"\t" * int(indent / TAB_WIDTH) if indent % TAB_WIDTH == 0 else " " * indent
		)

	@staticmethod
	def Require(name, paths=[]):
		"""Globs the given expressions replacing `{0}` with the given `name`,
		returning a list containing the file with the highest version number, or
		the list of matching files in case name contains a `*`.

		For instance:

		```
		>>> Require("select", ["lib/js"])
		(`lib/js/select-0.7.9.js`)
		```

		```
		>>> Require("module-*", ["lib/sjs"])
		(`lib/sjs/module-a.sjs`, `lib/sjs/module-b.sjs`)
		```

		"""
		for p in paths:
			p = p.format(name)
			matches = glob.glob(p)
			if not matches:
				continue
			if "*" in name:
				return sorted(matches, reverse=True)
			else:
				return (sorted(matches)[-1],)
		return ()

	@staticmethod
	def RequireExpand(parser, params, indent, patterns, template):
		"""A helper function that is used by `Require{CSS,JS}`, iterates
		on the hte given parameters, and injecting the template
		when files are found matching the patterns."""
		indent = PamlMacro.IndentAsString(indent)
		for f in params.split(","):
			f = f.strip()
			p = PamlMacro.Require(f, patterns)
			if p:
				# We make the path relative if there file has a different path
				parser_path = parser.path()
				if parser_path != ".":
					# NOTE: We're using dirname as the path is actually the
					# filename
					p = [os.path.relpath(_, os.path.dirname(parser_path)) for _ in p]
				if len(p) > 1:
					p = "+".join([p[0]] + [os.path.basename(_) for _ in p[1:]])
				else:
					p = p[0]
				if isinstance(template, types.FunctionType):
					parser._parseLine(template(indent, p))
				else:
					parser._parseLine(template.format(indent, p))

	def RequireCSS(parser, params, indent):
		"""The `require:css(name,...)` macro looks for files in the
		paths defined by `CSS_PATTERNS` for the given `name`s and
		replaces them by `<link>` tags."""
		PamlMacro.RequireExpand(
			parser,
			params,
			indent,
			PamlMacro.CSS_PATTERNS,
			"{0}<link(rel=stylesheet,type=text/css,href={1})",
		)

	def RequireJS(parser, params, indent):
		"""The `require:js(name,...)` macro looks for files in the
		paths defined by `JS` for the given `name`s and
		replaces them by `<script>` tags."""
		PamlMacro.RequireExpand(
			parser,
			params,
			indent,
			PamlMacro.JS_PATTERNS,
			"{0}<script(type=text/javascript,src={1})",
		)

	# NOTE: This should be deprecated
	def RequireGmodule(parser, params, indent):
		"""The `require:gmodule(name,...)` macro looks for files in the
		paths defined by `JS` for the given `name`s and
		replaces them by `<script>` tags."""
		# SEE: http://stackoverflow.com/questions/1918996/how-can-i-load-my-own-js-module-with-goog-provide-and-goog-require#2007296
		# We get the module names, and resolve them to files using deparse
		# FIXME: This is quite slow, we should try to factor this out as a
		# higher level operation
		modules = [_.strip() for _ in params.split(",")]
		files = (
			_[1] for _ in reduce(lambda x, y: x + y, deparse.find(modules).values(), [])
		)
		files = list(
			set((_ for _ in files if _.endswith(".sjs") or _.endswith(".gmodule.js")))
		)
		deps = [_[1] for _ in deparse.list(files)]
		# NOTE: This whole section should be refactored, and some of it
		# moved to deparse. In essence, what this does is:
		# 1) Takes a list of module names
		# 2) Finds these modules
		# 3) Parses each module
		# 4) Aggregate the js:* dependencies and recurse to 1
		# 5) The result is a list of [path, [provides‥], [requires‥]]
		for path in files:
			provides = deparse.provides(path)
			if not provides:
				continue
			type, name = provides[0]
			if name not in deps:
				deps.append(name)
		prefix = PamlMacro.IndentAsString(indent)
		base = os.path.dirname(os.path.abspath(parser.path()))
		count = 0

		def prefer_gmodule(path):
			"""Picks the gmodule file if available."""
			if path.endswith(".sjs"):
				return path + "?+google"
			else:
				name, ext = os.path.splitext(path)
				gpath = name + ".gmodule" + ext
				return gpath if os.path.exists(gpath) else path

		for name in deps:
			paths = [_[1] for _ in deparse.find(name)[name]]
			path = sorted(
				list(
					set(
						(
							_
							for _ in paths
							if _.endswith(".sjs") or _.endswith(".gmodule.js")
						)
					)
				)
			)
			if path:
				deps = [_[1] for _ in deparse.list(path)]
				path = prefer_gmodule(os.path.relpath(path[0], base))
				if count == 0:
					parser._parseLine(prefix + "<script@raw")
				line = (
					"{0}\tgoog.addDependency('../../../{1}',['{2}'],{3});\n{0}".format(
						prefix, path, name, json.dumps(deps)
					)
				)
				parser._parseLine(line)
				count += 1
		parser._parseLine("\n")

	def ImportJS(parser, params, indent):
		import deparse.core

		# We get the paths of the explicitely imported modules
		modules = flatten(
			[
				PamlMacro.Require(_.strip().replace(".", "/"), PamlMacro.JS_PATTERNS)
				for _ in params.split(",")
			]
		)
		# We retrieve the dependencies
		deps = deparse.core.list(modules, recursive=True, resolve=True)
		imports = []
		# We resolve the files
		for t, name in deps:
			imports += PamlMacro.Require(name.replace(".", "/"), PamlMacro.JS_PATTERNS)
		# And output the result
		prefix = PamlMacro.IndentAsString(indent)
		for path in imports + modules:
			# NOTE: If the module type is not Vanilla, we can use async
			line = "{0}<script(src='{1}')\n".format(prefix, path)
			parser._parseLine(line)

	# NOTE: This is declared here as we need to reference the Require*
	# class methods.
	CATALOGUE = {
		# NOTE: Requires are the old way of doing imports
		"require:css": RequireCSS,
		"require:js": RequireJS,
		"require:gmodule": RequireGmodule,
		# NOTE: This is the new way to do so
		"import:js": ImportJS,
	}


# EOF
