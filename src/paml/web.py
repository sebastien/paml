#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Project           :   PAML
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre           <sebastien.pierre@gmail.com>
# License           :   Lesser GNU Public License
# -----------------------------------------------------------------------------
# Creation date     :   2007-06-01
# Last mod.         :   2017-02-02
# -----------------------------------------------------------------------------

# TODO: Should be moved to retro

import os, sys, re, json, subprocess, tempfile, hashlib, threading, mimetypes, functools
from   paml import engine
try:
	import retro
	from   retro.contrib.localfiles import LocalFiles
	from   retro.contrib.cache      import SignatureCache, MemoryCache
	from   retro.contrib            import proxy
except ImportError as e:
	pass

# FIXME: Should have a context

SIG_CACHE       = SignatureCache ()
MEMORY_CACHE    = MemoryCache ()
PROCESSORS      = {}
COMMANDS        = None
NOBRACKETS      = None
PAMELA_DEFAULTS = {}
LOCKS           = {}
PANDOC_HEADER   = """
<!DOCTYPE html>
<html><head>
<meta charset="utf-8" />
<link rel="stylesheet" href="https://cdn.rawgit.com/sindresorhus/github-markdown-css/gh-pages/github-markdown.css" />
</head><body><div class="markdown-body" style="max-width:45em;padding:5em;">
"""
PANDOC_FOOTER = "</div></body></html>"

def getCommands():
	global COMMANDS
	if not COMMANDS:
		COMMANDS = dict(
			sugar       = os.environ.get("SUGAR",       "sugar"),
			coffee      = os.environ.get("COFFEE",      "coffee"),
			pythoniccss = os.environ.get("PYTHONICCSS", "pythoniccss"),
			pandoc      = os.environ.get("PANDOC",      "pandoc"),
			typescript  = os.environ.get("TYPESCRIPT",  "tsc"),
			babel       = os.environ.get("BABEL",       "babel"),
			hjson       = os.environ.get("HJSON",       "hjson"),
			texto       = os.environ.get("TEXTO",       "texto"),
			metablocks  = os.environ.get("METABLOCKS",  "metablocks"),
		)
	return COMMANDS

try:
	import templating
	HAS_TEMPLATING = templating
except:
	HAS_TEMPLATING = None


def locked(f):
	"""Ensures that the wrapped function is not executed concurrently."""
	def wrapper(*a, **kwa):
		name = f.__name__
		if name not in LOCKS: LOCKS[name] = threading.Lock()
		lock = LOCKS[name] ; lock.acquire()
		try:
			res = f(*a, **kwa)
			lock.release()
			return res
		except Exception as e:
			lock.release()
			raise e
			return None
	functools.update_wrapper(wrapper, f)
	return wrapper

def processPAML( pamlText, path, request=None ):
	parser = engine.Parser()
	parser.setDefaults(PAMELA_DEFAULTS)
	if request and request.get("as") == "js":
		parser._formatter = engine.JSHTMLFormatter()
		result = parser.parseString(pamlText, path)
		assign = request.get("assign")
		prefix = ""
		suffix = ""
		if assign:
			if assign == "_": assign = os.path.basename(path).split(".")[0]
			assign = assign.split(".")
			prefix = "var "
			suffix = ";"
			for i,v in enumerate(assign):
				if   i == 0:
					prefix += v + "=("
					suffix  = ")"    + suffix
				else:
					prefix += "{" + v + ":"
					suffix = "}" + suffix
		return prefix + result + suffix, "text/javascript"
	else:
		type = "text/html"
		if path.endswith(".xsl.paml"):
			# NOTE: Use text/xsl does not work in FF
			type = "text/xml"
		elif path.endswith(".xml.paml"):
			type = "text/xml"
		result = parser.parseString(pamlText, path)
		return result, type

def processPAMLXML( pamlText, path, request=None ):
	result, type = processPAML( pamlText, path, request )
	return result, "text/xml" if type == "text/html" else type

def processCleverCSS( text, path, request=None ):
	import clevercss
	result = clevercss.convert(text)
	return result, "text/css"

def cacheGet( text, path, cache ):
	"""Retrieves the given data from the cache. If path is given, then
	the `SIG_CACHE` will be used, testing the `mtime` of the file at the
	given path.

	Note that `path` can contain a query string, which will be striped to
	acces the mtime."""
	if cache:
		if path:
			# The path might have a query string, in which case we remove it
			subpath       = path.split("?",1)[0]
			cache         = SIG_CACHE
			timestamp     = SignatureCache.mtime(subpath)
			# We get/set using the actual path, not the subpath
			is_same, data = cache.get(path,timestamp)
			return cache, is_same, data, timestamp
		else:
			text    = engine.ensure_unicode(text)
			sig     = hashlib.sha256(bytes(u" ".join(command) + text)).hexdigest()
			cache   = MEMORY_CACHE
			is_same = cache.has(sig)
			data    = cache.get(sig)
			return cache, is_same, data, sig
	else:
		return cache, False, None, None

# FIXME: The caching infrastructure should not be dependent on the path
# only. For instance, we might want to cache the same file, but compiled
# with different command (options).
def _processCommand( command, text, path, cache=True, tmpsuffix="tmp",
		tmpprefix="paml_", resolveData=None, allowEmpty=False, cwd=None):
	timestamp = has_changed = data = None
	error = None
	cache, is_same, data, cache_key = cacheGet( text, path, cache)
	if (not is_same) or (not cache):
		if not path or os.path.isdir(path):
			temp_created = True
			fd, path     = tempfile.mkstemp(suffix=tmpsuffix,prefix=tmpprefix)
			os.write(fd, engine.ensure_bytes(text))
			os.close(fd)
			command = command[:-1] + [path]
		else:
			temp_created = False
		# FIXME: Honestly, I have so many problems with popen it's unbelievable.
		# I sometimes get sugar to freeze without any reason. I'm keeping the
		# following snippet for reference of what not to do.
		# ---
		# cmd     = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE,
		# 		stderr=subprocess.PIPE, cwd=cwd)
		# data    = cmd.stdout.read()
		# error   = cmd.stderr.read()
		# print ("  data",  repr(data))
		# print ("  error", repr(error))
		# print ("waiting...")
		# cmd.wait()
		# ---
		# Here the `shell` means single-line comman,d
		p  = subprocess.Popen(" ".join(command), shell=True,
				stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True,
				cwd=cwd)
		data, error = p.communicate()
		# DEBUG:
		# If we have a resolveData attribute, we use it to resolve/correct the
		# data
		if temp_created:
			os.unlink(path)
		if not data and resolveData:
			data = resolveData()
		if not data and not allowEmpty:
			raise Exception(error or u"No data processing `{0}`".format(u" ".join(command)))
		if not temp_created and not error:
			# We don't cache temp files. Temp files are only created when
			# we don't have a path.
			if cache is SIG_CACHE:
				cache.set(path,cache_key,data)
				assert cache.has(path, cache_key)
			elif cache is MEMORY_CACHE:
				cache.set(cache_key,data)
				assert cache.has(cache_key) == data
	assert data is not None, "paml.web._processCommand: None returned by {0}".format(command)
	return engine.ensure_unicode(data), error

@locked
def processSugar( text, path, request=None, cache=True, includeSource=False ):
	text        = engine.ensure_unicode(text or "")
	multi_paths = None
	sugar       = getCommands()["sugar"]
	# NOTE: This supports having multiple paths given as argument, which
	# will then be combined as a single argument.
	options     = []
	query       = ""
	# If we have + in the request query, then we interpret that as a reset
	# of default sugar options, which we make sure are stripped from the
	# default options.
	if request:
		query = request.path().split("?",1)
		if len(query) == 2:
			if "+" in query[1]:
				options = ["-D" + _.strip() for _ in query[1].split("+") if _.strip()]
				sugar   = " ".join(_ for _ in sugar.split() if not _.startswith("-D"))
			query = "?" + query[1]
		else:
			query = ""
	if isinstance(path, tuple) or isinstance(path, list):
		multi_paths = path
		path        = path[0]
	if os.path.isdir(path or "."):
		parent_path  = path or "."
	else:
		parent_path  = os.path.dirname(os.path.abspath(path or "."))
	# We create a temp dir to cd to, because sugar's DParser
	# creates temp files in the current dir.
	temp_output = None
	if not path:
		temp_output = tempfile.mktemp()
		path        = temp_output
		with open(temp_output, "w") as f:
			f.write(text.encode("utf-8"))
	temp_path = tempfile.mkdtemp()
	norm_path = lambda _:os.path.relpath(_, temp_path)
	if not os.path.exists(temp_path): os.mkdir(temp_path)
	# Options
	sugar_backend = os.environ["SUGAR_BACKEND"] if "SUGAR_BACKEND" in os.environ else "js"
	# Otherwise we fallback to the regular Sugar, which has to be
	# run through popen (so it's slower)
	command = [
		sugar,
		("-cSl" if includeSource else "-cl") + sugar_backend,
		"-L" + os.path.abspath(os.path.join(os.getcwd(), "lib/sjs")),
		"-L" + os.path.abspath(os.path.join(os.getcwd(), "src/sjs")),
		"-L" + norm_path(parent_path),
		"-L" + norm_path(os.path.join(parent_path, "lib", "sjs")),
	] + options + [
		" ".join(norm_path(_) for _  in multi_paths) if multi_paths else norm_path(path)
	]
	res, error = _processCommand(command, text, path + query, cache, cwd=temp_path)
	if error and not(res.strip()):
		res = "console.error("+ json.dumps(error) +")"
	# We clean up the temp dir
	if os.path.exists(temp_path): os.rmdir(temp_path)
	if temp_output and os.path.exists(temp_output): os.unlink(temp_output)
	return res, "text/javascript"

def processCoffeeScript( text, path, request=None, cache=True ):
	command = [
		getCommands()["coffee"],"-cp",
		path
	]
	return _processCommand(command, text, path, cache)[0], "text/javascript"

def processBabelJS( text, path, cache=True ):
	command = [
		getCommands()["babel"],
		path
	]
	return _processCommand(command, text, path, cache)[0], "text/javascript"

def processTypeScript( text, path, request=None, cache=True ):
	timestamp = has_changed = data = None
	cache, is_same, data, cache_key = cacheGet( text, path, cache)
	if (not is_same) or (not cache):
		# We get the process through `tsc`
		temp_path = tempfile.mktemp(prefix="pamlweb-", suffix=".ts.js")
		command = [
			getCommands()["typescript"], "--outFile", temp_path, "--module", "amd", path
		]
		def read_file():
			if os.path.exists(temp_path):
				with file(temp_path) as f:
					return f.read()
			return None
		# We bypass the cache
		error,_ = _processCommand(command, text, path, cache=None, resolveData=read_file)
		data  = None
		# We don't expect to have an error there
		# if error.strip():
		# 	return "<html><body><pre>%s</pre></body></html>".format(error), "text/html"
		# NOTE: TypeScript does not support output to stdout
		if os.path.exists(temp_path):
			with file(temp_path) as f:
				data = f.read()
			os.unlink(temp_path)
		if error and error != data:
			data = "\n//\t".join(["// ERROR: {0}\n//".format(" ".join(command))] + error.split("\n")) + "\n" + data
		# Now we retrieve the cache
		if cache is SIG_CACHE:
			cache.set(path,cache_key,data)
			assert cache.has(path, cache_key)
		elif cache is MEMORY_CACHE:
			cache.set(cache_key,data)
			assert cache.has(cache_key) == data
	return data,"text/javascript"

def processPandoc( text, path, request=None, cache=True ):
	command = [
		getCommands()["pandoc"],
		path
	]
	return PANDOC_HEADER + _processCommand(command, text, path, cache)[0] + PANDOC_FOOTER, "text/html"


def processPythonicCSS( text, path, request=None, cache=True ):
	# NOTE: Disabled until memory leaks are fixed
	# import pythoniccss
	# result = pythoniccss.convert(text)
	# return result, "text/css"
	command = [
		getCommands()["pythoniccss"],
		path
	]
	return _processCommand(command, text, path, cache, allowEmpty=False)[0], "text/css"

def processHJSON( text, path, request=None, cache=True ):
	import hjson
	result = hjson.loads(text)
	return hjson.dumpsJSON(result), "application/json"

def processTexto( text, path, request=None, cache=True ):
	import texto.main
	if request and request.param("as") == "raw":
		return text, "text/plain"
	else:
		result = u"<!DOCTYPE html>\n" + texto.main.text2htmlbody(engine.ensure_unicode(text))
		if request:
			result = "<div><small><a href='{0}'>[SOURCE]</a></small></div>".format(request.path() +
			"?as=raw") + result
		return result, "text/html"

def processNobrackets( text, path, request=None, cache=True ):
	"""Processes the given `text` (that might come from the given path)
	through nobrackets. Nobrackets will in turn invoke sub-processors
	based on the `path` extension."""
	# We ensure that NOBRACKETS references a nobrackets processor,
	# and is properly initialized.
	global NOBRACKETS
	if not NOBRACKETS:
		import nobrackets
		p   = nobrackets.Processor()
		p.registerExtensions(nobrackets)
		NOBRACKETS = p
	# Now we try to retrieve either the text or the path from
	# the cache.
	cache, is_same, data, cache_key = cacheGet (text, path, cache)
	cache_path = path
	if (not is_same) or (not cache):
		# If the contents has changed, or if we did not cache, we'll
		# process the text/path through nobrackets and create an output
		assert path, "Nobrackets is only supported for files, for now"
		res      = NOBRACKETS.processPath(path)
		# We trim the path from the .nb extension, retrieve the actual
		# extension and write the result to a temp file with the
		# proper extension
		path     = NOBRACKETS.trimExtension(path)
		ext      = path.rsplit(".",1)[-1]
		res_path = "{0}/temp-nobrackets-{1}".format(os.path.dirname(os.path.abspath(path)), os.path.basename(path))
		with file(res_path, "w") as f: f.write(res)
		# We not look in the processors for a matching processor
		proc = getProcessors()
		if ext in proc:
			# We don't want to cache here as we're already doing the cachgin
			res, content_type = proc[ext](res, res_path, cache=False)
			content_type      = content_type or "text/plain"
		else:
			content_type = mimetypes.guess_type(path)
			content_type = (content_type[0] if content_type else None) or "text/plain"
		assert content_type
		# We cleanup the temp file
		# if os.path.exists(res_path): os.unlink(res_path)
		# Now for caching-friendlyness, we store the content_type in addition
		# to the data
		data = content_type + "\t" + res
		if   cache is SIG_CACHE:
			cache.set(cache_path, cache_key, data)
		elif cache is MEMORY_CACHE:
			cache.set(cache_key, data)
		return res, content_type
	else:
		# We can retrieve the content from the cache
		content_type, data = data.split("\t", 1)
		return data, content_type

def processBlock( text, path, request=None, cache=True ):
	"""Processes the given `.block` file."""
	import metablocks
	cache, is_same, data, cache_key = cacheGet (text, path, cache)
	cache_path = path
	is_same = False
	if (not is_same) or (not cache):
		data = metablocks.process(text, path=path, xsl="lib/xsl/block.xsl")
		if   cache is SIG_CACHE:
			cache.set(cache_path, cache_key, data)
		elif cache is MEMORY_CACHE:
			cache.set(cache_key, data)
		return data, "text/xml"
	else:
		return data, "text/xml"

def getProcessors():
	"""Returns a dictionary with the Retro LocalFiles processors already
	setup."""
	global PROCESSORS
	if not PROCESSORS:
		PROCESSORS = {
			"xml.paml" : processPAMLXML,
			"xsl.paml" : processPAMLXML,
			"paml"     : processPAML,
			"sjs"      : processSugar,
			"js6"      : processBabelJS,
			"es6.js"   : processBabelJS,
			"ccss"     : processCleverCSS,
			"coffee"   : processCoffeeScript,
			"hjson"    : processHJSON,
			"texto"    : processTexto,
			"txto"     : processTexto,
			"ts"       : processTypeScript,
			"pcss"     : processPythonicCSS,
			"md"       : processPandoc,
			"nb"       : processNobrackets,
			"block"    : processBlock,
		}
	return PROCESSORS

def resolveFile( component, request, path ):
	"""A custom path resolution function that will alias `.ts.js` files
	to `.ts` files."""
	p = component._resolvePath(path)
	if not os.path.exists(p):
		name = p.rsplit(".", 1)[0]
		if p.endswith(".ts.js"):
			return p[0:-3]
		if p.endswith(".js"):
			_ = p[0:-3]
			for e in (".ts", ".sjs", ".es6.js"):
				if os.path.exists(_ + e):
					return _ + e
		if p.endswith(".css") and os.path.exists(name + ".pcss"):
			return name + ".pcss"
		# Automatically adds paml suffix
		if p.endswith(".xml") or p.endswith(".xsl") and os.path.exists(p + ".paml"):
			return p + ".paml"
		# We alias .hsjon to .json if there is no .json
		if p.endswith(".json") and os.path.exists(name + ".hjson"):
			return name + ".hjson"
	if not os.path.exists(p) and "+" in p:
		prefix = os.path.dirname(p)
		paths  = p.split("+")
		res    = [paths[0]] + [os.path.join(prefix,_) for _ in paths[1:]]
		return res
	return p

def getLocalFiles(root=""):
	"""Returns a Retro LocalFile component initialized with the PAML
	processor."""
	return LocalFiles(root=root,processors=getProcessors(),resolver=resolveFile,optsuffix=[".paml",".html"], lastModified=False, writable=True)

def run( arguments, options={} ):
	import argparse
	p = argparse.ArgumentParser(description="Starts a web server that translates PAML files")
	p.add_argument("values",  type=str, nargs="*")
	p.add_argument("-d", "--def", dest="var",   type=str, action="append")
	args      = p.parse_args(arguments)
	options.update(dict(_.split("=",1) for _ in args.var or ""))
	options.update(dict((_.split("=",1)[0].lower(), _.split("=",1)[1]) for _ in args.values or "" if not _.startswith("proxy:")))
	# We can load defaults. This should be moved to a dedicated option.
	global PAMELA_DEFAULTS
	defaults_path = ".paml-defaults"
	if os.path.exists(defaults_path):
		with open(defaults_path) as f:
			PAMELA_DEFAULTS = json.load(f)
	processors = getProcessors()
	if "plain" in options:
		for v in options["plain"].split(","):
			del processors[v.strip()]
	files   = getLocalFiles()
	comps   = [files]
	proxies = [x[len("proxy:"):] for x in [x for x in args.values if x.startswith("proxy:")]]
	comps.extend(proxy.createProxies(proxies))
	app     = retro.Application(components=comps)
	retro.command(
		[_ for _ in args.values],
		app      = app,
		port     = int(options.get("port") or retro.DEFAULT_PORT)
	)

# -----------------------------------------------------------------------------
#
# MAIN
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
	options = {}
	#for a in sys.argv[1:]:
	#	a=a.split("=",1)
	#	if len(a) == 1: v=True
	#	else: v=a[1];a=a[0]
	#	options[a.lower()] = v
	run(sys.argv[1:], options)

# EOF - vim: tw=80 ts=4 sw=4 noet
