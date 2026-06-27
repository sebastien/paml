import os
import sys
import re
import tempfile
import shutil
import subprocess

IS_PYTHON3 = sys.version_info[0] > 2

if IS_PYTHON3:
	unicode = str


def ensureUnicode(t, encoding="utf8"):
	if IS_PYTHON3:
		if isinstance(t, str):
			return t
		try:
			return str(t, encoding)
		except UnicodeDecodeError:
			return str(t, encoding, errors="replace")
	else:
		return t if isinstance(t, unicode) else t.decode(encoding)


def ensureBytes(t, encoding="utf8"):
	if IS_PYTHON3:
		return t if isinstance(t, bytes) else bytes(t, encoding)
	else:
		return t


def _guessSourceEncodings(data):
	encodings = []
	if data.startswith(b"\xef\xbb\xbf"):
		encodings.append("utf-8-sig")
	match = re.search(rb'encoding=["\']([A-Za-z0-9._-]+)["\']', data[:256])
	if match:
		encodings.append(match.group(1).decode("ascii", "ignore"))
	encodings.extend(("utf-8", "iso-8859-1", "latin-1"))
	result = []
	for encoding in encodings:
		if encoding and encoding not in result:
			result.append(encoding)
	return result


def decodeSourceBytes(data, fallback="utf-8"):
	for encoding in _guessSourceEncodings(data):
		try:
			return data.decode(encoding)
		except (LookupError, UnicodeDecodeError):
			pass
	return data.decode(fallback, errors="replace")


def readSourceLines(path):
	with open(path, "rb") as f:
		return decodeSourceBytes(f.read()).splitlines(True)


def _runEmbeddedCommand(command, source, path_suffix=""):
	if not command or not shutil.which(command[0]):
		return source
	with tempfile.NamedTemporaryFile("wb", suffix=path_suffix, delete=False) as handle:
		handle.write(ensureBytes(source))
		temp_path = handle.name
	try:
		completed = subprocess.run(
			command + [temp_path],
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			check=False,
		)
		if completed.returncode != 0:
			return source
		output = completed.stdout or b""
		return decodeSourceBytes(output) if output else source
	finally:
		if os.path.exists(temp_path):
			os.unlink(temp_path)


def flatten(values, result=None):
	result = result or []
	[
		(
			result.extend(flatten(_))
			if isinstance(_, list) or isinstance(_, tuple)
			else result.append(_)
		)
		for _ in values
	]
	return result


def xslEscape(text):
	text = text.replace("\n", "&#x000A;")
	text = text.replace("\t", "&#x0020;")
	text = text.replace(">", "&gt;")
	text = text.replace("<", "&lt;")
	return text


def xmlEscape(text):
	# TODO: Support escaping &
	text = text.replace("<", "&lt;")
	text = text.replace(">", "&gt;")
	return text


# EOF
