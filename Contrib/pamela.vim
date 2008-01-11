" Vim syntax file
" Language:   Pamela (http://www.ivy.fr/pamela)
" Authors:    Sebastien Pierre <sebastien@type-z.org>
"             Maxime Dupuis <maxime@akoha.org>
" Maintainer: Sebastien Pierre <sebastien@type-z.org>
" Created:    2007-09-12
" Updated:    2008-01-11

" Tag classes, ids, labels
syn match   pamelaId            "#[A-Za-z0-9_-]*"       contained   nextgroup=pamelaClassSep,pamelaLabel
syn match   pamelaClassSep      "\."                    contained   nextgroup=pamelaClass
syn match   pamelaClass         "[A-Za-z0-9_-]*"        contained   nextgroup=pamelaClassSep,pamelaLabel,pamelaId
syn match   pamelaLabel         ":.*"                   contained

" Tags
syn match   pamelaTag           "\s*<\w*[^\W\(\.#:]"    nextgroup=pamelaId,pamelaClassSep,pamelaLabel,pamelaAttributes,pamelaClass
syn region  pamelaAttributes    start=+(+ end=+)+       contains=pamelaAttribute,pamelaAttribueVal,pamelaAttributeSep
syn match   pamelaAttribute     "[A-Za-z0-9_-]*="       contained nextgroup=pamelaAttributeVal
syn match   pamelaAttributeVal  "[^,\)]*"               contained nextgroup=pamelaAttributeSep
syn match   pamelaAttributeSep  ","                     contained nextgroup=pamelaAttribute

" Everything else
syn match   pamelaComment       "^\s*#.*$"              contains=pamelaCommentAnn
syn match   pamelaCommentAnn    /\v(TODO|NOTE|FIXME|BUG|SEE|WARNING|EOF).*/ contained

" Django Templates
syn match   pamelaDjango        "^\s*{%.*%}\s*"
syn match   htmlEntity          "&[^; \t]*;"            contains=sgmlEntityPunct

syn region  pamelaString        start=+'+ skip=+\\\\\|\\'\|\\$+ excludenl end=+'+ end=+$+ keepend
syn region  pamelaString        start=+"+ skip=+\\\\\|\\"\|\\$+ excludenl end=+"+ end=+$+ keepend

"-------------------------------------------------

hi def link pamelaComment       Comment
hi def link pamelaTag           Statement
hi def link pamelaDjango        Special
hi def link htmlEntity          Number

hi def link pamelaId            Identifier
hi def link pamelaClassSep      Normal
hi def link pamelaClass         Identifier
hi def link pamelaLabel         Constant

hi def link pamelaAttributes    Statement
hi def link pamelaAttribute     Statement
hi def link pamelaAttributeVal  Constant
hi def link pamelaAttributeSep  Type

hi def link pamelaCommentAnn    Todo
hi def link pamelaString        String

" Default text settings for Pamela files
set textwidth=80
set noet
set ts=4
set sw=4

" This does not work, I don't know why :/
let b:current_syntax = "pamela"

" EOF
