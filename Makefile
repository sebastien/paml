DOCS=MANUAL.html ROADMAP.html Documentation/pamela-api.html
SOURCES=\
	Sources/pamela/engine.py \
	Sources/pamela/web.py

doc: $(DOCS)
	@echo Documentation ready

%-api.html:  $(SOURCES)
	sdoc -c $^ $@

%.html: %.txt
	kiwi $< $@

# EOF
