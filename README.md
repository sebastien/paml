== Paml
== Brings the pleasure back to HTML and XML !
-- Author: Sébastien Pierre <sebastien@ivy.fr>
-- Date:     03-Oct-2009
-- Creation: 24-Aug-2007

Introduction
============

  People who care about web application design and development know that it's
  better to write your HTML by hand rather than using a tool to produce it. The
  reasons are that you know and control the information and the structure of
  your documents, which is a critical aspect when your HTML is the basis for a
  JavaScript-driven rich client application.

  Writing HTML is quite painful, and you have some tools out there to help you
  in this task. You can use templating languages like Cheetah or KID (Python) or
  RHTML (Ruby) to make your life easier and encourage re-use of bits of code -- 
  but you may find that process a bit too complicated for your daily usage.

  Some people tried to make writing HTML easier, the [HAML][HAML]
  or [SLIP][SLIP] projects are good examples of that. However, HAML is too tied
  to Ruby and RHTML, and SLIP was not flexible enough and a bit outdated.

  Pamela is an attempt at following the path of HAML and SLIP, while improving
  on some aspects:

  Be simple:: while there is a need for include/import of elements, there is no
    need for supporting a full templating system. This helps keep the syntax
    sane and easy.

  Less errors:: it is easy to make mistakes when you write HTML (forget to
    close tags, empty divs that are removed by the browser), so Pamela's syntax
    is designed to prevent errors and maximize re-use and readability.

  Does one thing, but does it very well:: we do not want to introduce features
    tied to a specific technology not related to HTML. Pamela will only output
    HTML/XML, and does not try to be a full templating language. Pamela does its
    best to offer you the most flexibility in producing the HTML document that
    you want.

  For designers and developers:: whether you quickly want to prototype your
    design or define CSS classes and ids to hook your JavaScript on, Pamela will
    make it easy and quick to do what you want and help people understand your
    design.

  Pamela's syntax was designed to be very easy to learn, to be consistent, to
  favor explicit over implicit, and to allow people to quickly write HTML code.

Getting started
===============

Dive into Pamela
================

  1. Basics
  =========

  First things first, let's start with a simple Pamela example:

  >   <html
  >     <head
  >       <title:My first Pamela document
  >     <body
  >       <h1:Lorem ipsum
  >       <p
  >         Lorem <b:ipsum dolor sit amet>, consectetuer adipiscing elit. Sed
  >         feugiat, dui eu condimentum porttitor, nisi erat ultrices elit, in
  >         sagittis sapien quam sed dolor. 

  this example will be translated to

  >   <html>
  >       <head>
  >           <title>My first Pamela document</title>
  >       </head>
  >       <body>
  >           <h1>Lorem ipsum</h1>
  >           <p>
  >               Lorem <b:ipsum dolor sit amet>, consectetuer adipiscing elit. Sed
  >               feugiat, dui eu condimentum porttitor, nisi erat ultrices elit, in
  >               sagittis sapien quam sed dolor. 
  >           </p>
  >       </body>
  >   </html>

  This quick example can give you a good idea of the basic principles of Pamela:

  - Pamela is indentation-driven:: the indentation defines which tag is the
    parent tag.

  - Pamela elements can be inlined:: you're not forced to indent all your tags,
    and you can simply inline your tags, taking care of explicitely closing
    them.

  As a summary, here are the syntactic elements presented in the above example:

  2. CSS and IDs
  ==============

  This basic knowledge will allow you to create simple HTML documents. If you're
  working on HTML documents that will be part of a web application or make some
  intensive use of CSS, you'll want to specify _classes and ids_ for your HTML
  elements.

  You can use the default syntax to do that

  >   <div(id=mydiv,class=classA classB)
  
  however, you have a more convenient way of doing the same:

  >   <div#mydiv.classA.classB

  where you indicate your element id with '#ID' and the classes as '.class'
  appended to your element.


  3. Content declaration and inclusion
  ====================================

  When you'll start writing more complex Pamela document, you may want to avoid
  having too many levels of nested elements. A good way to do that is to define
  specific subsets of your HTML document, and then assign them to be the content
  for specific elements:

  >   @head
  >     <title:My document
  >     <link(rel=Stylesheet,media=screen,type=text/css,href=screen.css)
  >   @content
  >     <h1:Lorem ipsum
  >     <p:Dolor sit amet
  >   
  >   <html
  >     <head=@head
  >     <body
  >       <div=@content

  will result into

  <<<
    TODO
  >>>


  4. JavaScript and CSS support
  =============================

  Last but not least, you may want to indicate that parts of your HTML documents
  are expressed in a specific language, say for instance CSS. Pamela allows you
  to declare that:

    <<<
    @style:[css|
      html, body {
        margin:  0;
        padding: 0;
      }
      #toolbar ul {
        list-style-type: none;
      }
    ]
    >>>

  this gives you the opportunity to process the data contained within the
  '[...]' as a specific kind of content. As always, content indentation is
  required for this block to be valid.


  5. HTML rendering hints
  =======================

  If you're very picky about the way your HTML document looks like, you'll
  probably find the _rendering hints_ useful. Let's look at the following HTML
  code:

  # TODO: Mention single line and multi-line

    <<<
      <h1>Lorem ipsum</h1>
      <p>Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean ante leo,
      suscipit sit amet, iaculis sed, rutrum eu, mi. Aenean laoreet, erat
      consequat aliquam tempor, nibh nisl porta augue, in condimentum nunc sem sed
      nunc. Duis a justo. Integer tincidunt, nisi lacinia pretium sollicitudin,

      dui sapien pharetra urna, in viverra augue quam vel eros. Nulla risus.
      Praesent nec orci eget lectus imperdiet posuere. Mauris bibendum blandit
      turpis. Quisque urna. Donec enim quam, ultricies at, dictum tempus, molestie
      quis, urna. Maecenas pretium dignissim massa. Quisque nisi.</p>
    >>>

  Adding rendering hints to your elements is quite easy: you simply have to
  append '|' and a letter to your tag name, after the id, classes and attributes
  definition:

  >   <span|s
  >   <div#mydiv.myClass(attr=value)|s

  all tell that the resulting HTML content should be stripped ('s' rendering
  hint). You can just add letters to add more rendering hints.

  Single-line ('sl')::
    indicates that you want your HTML element to be rendered on a
    single line (which may be wrapped if you specified a text width)
    |
    >   <h1|sl:
    >     Lorem ipsum dolor
    >     sit amet
    |
    will be rendered as
    |
    >   <h1>Lorem ipsum dolor sit amet</h1>

  Inline ('i')::
    inlines will be written as single-lines when their content do not have any
    newline '\n':
    |
    >   <script|i:alert("Hello");
    |
    will be rendered as
    |
    >   <script>alert("Hello");</script>
    |
    while
    |
    >   <script
    >     alert("Hello");
    |
    will be rendered as
    >   <script>
    >      alert("Hello");
    >   </script>

  Wrap (default, 'w')::
    tells that the content should be wrapped to the text width (set to 80 by
    default). This is especially for paragraphs:
    |
    >   <p>
    >     Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean ante leo,
    >     suscipit sit amet, iaculis sed, rutrum eu, mi. Aenean laoreet, erat
    >     consequat aliquam tempor, nibh nisl porta augue, in condimentum nunc sem sed
    >     nunc. Duis a justo. Integer tincidunt, nisi lacinia pretium sollicitudin
    >   </p>
    |
    instead of having everything on a single line
    |
    >   <p>
    >     Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean ante leo...
    >   </p>

  Preserve ('p')::
    tells that the text content should be preserved ''as-is'', which is
    espectially useful for preformatted elements:
    |
    >   <pre|p
    >     def myPythonFunction(a,b):
    >       print "Hello, ", someone, "!"
    |
    will be rendered as
    |
    >   <pre>  def myPythonFunction(a,b):
    >     print "Hello, ", someone, "!"</pre>

  Normalize ('n')::
    indicates that you want '\n' and '\t' to be converted to spaces,
    and multiple spaces to be compressed into one.
    |
    >    <code:   Lorem    ipsum
    >         dolor    sit amet
    |
    will be rendered as
    |
    >    <code> Lorem ipsum dolor sit amet</code>

  Strip ('s')::
    indicates that you want your string content to be stripped out leading
    and trailing spaces.
    |
    >   <h1|s:  Stripped heading
    |
    will be rendered as
    |
    >   <h1>Stripped heading</h1>

  Compact ('c')::
    tells that no new-lines or spaces should be inserted before and after the
    opening tag, like in the following example 
    |
    >   <p|c
    >     Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean ante leo,
    >     suscipit sit amet, iaculis sed, rutrum eu, mi. Aenean laoreet, erat
    >     consequat aliquam tempor, nibh nisl porta augue.
    |
    will be rendered as
    |
    >     <p>Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean ante leo,
    >     suscipit sit amet, iaculis sed, rutrum eu, mi. Aenean laoreet, erat
    >     consequat aliquam tempor, nibh nisl porta augue.</p>
    |
    instead of 
    |
    >     <p>
    >       Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean ante leo,
    >       suscipit sit amet, iaculis sed, rutrum eu, mi. Aenean laoreet, erat
    >       consequat aliquam tempor, nibh nisl porta augue.
    >     </p>


  Additionaly you can define specific hints for classes of elements, by using
  declarations. If you want to define that 'pre' and 'code' elements should be
  'preserved', you can do this (preferably at the top of your document)

  >   @pre,code|preserved

  6. Including other Pamela files
  ===============================

  It's likely that at some point you'd like to have a library of Pamela files
  with already defined snippets of Pamela code, whether it's specific rendering
  hints or pre-defined declarations.

  To include a file 'library.paml' file that resides in the same directory as your current
  Pamela file, just do the following:

  >    %include library

  if there is no 'library.paml' file in the current directory, you can also
  define a 'PAMELA_LIBRARY' environment variable that points to a specific
  directory containing your '.paml' files.

  If this directory also has subdirectories like 'widget/datepicker.paml', you
  can do:
  
  >   %include widget/datepicker

  to include the 'widget/datepicker.paml' from your library into your current
  document. It is a good practice to collect some library of snippets that can
  be easily be re-used among your various HTML documents.

  You can also specify *replacement values* for variables declared in the included paml
  file as '${VARIABLE}'. For instance:

  >   %include widget/datepicker {ID=mywidget,TITLE="Start date"}

  with 'widget/datepicker.paml' being something like:

  >    <div#${ID}.DatePicker
  >       <h3.title:${TITLE}

  this is an easy way to make generic '.paml' snippets that can be used as ''templates'' 
  for specific elements.

  In case you want to add additional class attributes or specific attributes, you can
  add (and override) the included elements attributes by doing:

  >   %include widget/datepicker +.Imported(date=2009-10-23)

  in the above example, the 'widget/datepicker.paml' snippet will be included, the 
  'Imported' class will be added to the element class attributes and a 'date' attribute
  will be set with the value '2009-10-23'.

  7. Ideas about using Pamela
  ===========================

  If you're like me and have stopped using XML as a data-format because there
  was no simple editor, you should really consider Pamela. Pamela can be great
  for hand-writing XML code specific to your application.

  Let's take the FOAF or RDF XML applications...


  8. Quick reference
  ==================

  == Pamela elements basic syntax
  =============================================================================
  Element           || Syntax                     || HTML
  =============================================================================
  _inlined element_ || '<tag:...>'                || '<tag>...</tag>'
  -----------------------------------------------------------------------------
  Here is an example where you use 'span' and 'a' elements:
  >   Lorem <span:ipsum dolor> sit <a(href=http://www.google.com):amet> 
  ------------------++---------------------------------------------------------
  _block element_   || >   <tag                   || '<tag>Lorem ipsum</tag>'
                    || >     Lorem ipsum          ||
  ------------------++---------------------------------------------------------
  _attributes_      || '<a(href=http://...):link' || '<a href="http://...">link</a>'
  =============================================================================

  == Pamela ID and class specification
  =====================================================================================
  Element           || Syntax                  || HTML
  =====================================================================================
  _element id_      || '<tag#myid:...>'        || '<tag id="myid">...</tag>'
  -------------------------------------------------------------------------------------
  _element class_   || '<span.mySpanClass:...' || '<span class="mySpanClass>...</span>'
  =====================================================================================


  == Pamela element declaration and inclusion
  =============================================================================
  Element               || Syntax
  =============================================================================
  _element declaration_ || '@element'
  -----------------------------------------------------------------------------
  _element reference_   || '<div=@element'
  =============================================================================


  == Declaration of specific languages
  =============================================================================
  Element                   || Syntax                   
  =============================================================================
  _css declaration_         || '<div:[css|...]'
  -----------------------------------------------------------------------------
  _javascript declaration_  || '<script:[javascript|...]'
  =============================================================================

# --

 [HAML]: HAML ''markup haiku'', <http://haml.hamptoncatlin.com/tutorial>
 [SLIP]: Slip, a "Sorta Like Python" shorthand for XML,
         <http://slip.sourceforge.net/>
 [YAML]: Yet Another Markup Language <http://www.yaml.org>

# vim: syn=kiwi ts=2 sw=2 et
