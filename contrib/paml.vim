" Vim syntax file
" Language:   PAML (http://www.ivy.fr/paml)
" Authors:    Sebastien Pierre <sebastien@type-z.org>
"             Maxime Dupuis <maxime@akoha.org>
" Maintainer: Sebastien Pierre <sebastien@type-z.org>
" Created:    2007-09-12
" Updated:    2008-01-11

" Tag classes, ids, labels
syn match   pamlId            "#[A-Za-z0-9_-]*"       contained   nextgroup=pamlClassSep,pamlLabel
syn match   pamlClassSep      "\."                    contained   nextgroup=pamlClass
syn match   pamlClass         "[A-Za-z0-9_-]*"        contained   nextgroup=pamlClassSep,pamlLabel,pamlId
syn match   pamlLabel         ":.*"                   contained

" Tags
syn match   pamlTag           "\s*<\w*[^\W\(\.#:]"    nextgroup=pamlId,pamlClassSep,pamlLabel,pamlAttributes,pamlClass
syn region  pamlAttributes    start=+(+ end=+)+       contains=pamlAttribute,pamlAttribueVal,pamlAttributeSep
syn match   pamlAttribute     "[A-Za-z0-9_-]*="       contained nextgroup=pamlAttributeVal
syn match   pamlAttributeVal  "[^,\)]*"               contained nextgroup=pamlAttributeSep
syn match   pamlAttributeSep  ","                     contained nextgroup=pamlAttribute

" Everything else
syn match   pamlComment       "^\s*#.*$"              contains=pamlCommentAnn
syn match   pamlCommentAnn    /\v(TODO|NOTE|FIXME|BUG|SEE|WARNING|EOF).*/ contained

" Django Templates
syn match   pamlDjango        "^\s*{%.*%}\s*"
syn match   htmlEntity          "&[^; \t]*;"            contains=sgmlEntityPunct

syn region  pamlString        start=+'+ skip=+\\\\\|\\'\|\\$+ excludenl end=+'+ end=+$+ keepend
syn region  pamlString        start=+"+ skip=+\\\\\|\\"\|\\$+ excludenl end=+"+ end=+$+ keepend

"-------------------------------------------------

hi def link pamlComment       Comment
hi def link pamlTag           Statement
hi def link pamlDjango        Special
hi def link htmlEntity          Number

hi def link pamlId            Identifier
hi def link pamlClassSep      Normal
hi def link pamlClass         Identifier
hi def link pamlLabel         Constant

hi def link pamlAttributes    Statement
hi def link pamlAttribute     Statement
hi def link pamlAttributeVal  Constant
hi def link pamlAttributeSep  Type

hi def link pamlCommentAnn    Todo
hi def link pamlString        String

" Default text settings for PAML files
set textwidth=80
set noet
set ts=4
set sw=4

" This does not work, I don't know why :/
let b:current_syntax = "paml"

" EOF
