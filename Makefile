SOURCES     = $(wildcard Sources/*/*.py)
MANIFEST    = $(SOURCES) $(wildcard Sources/*/*.py api/*.* AUTHORS* README* LICENSE*)
VERSION     = `grep -r VERSION src.py | head -n1 | cut -d '=' -f2  | xargs echo`
OS          = `uname -s | tr A-Z a-z`
PRODUCT     = MANIFEST

.PHONY: all doc clean check tests

all: $(PRODUCT)

release: $(PRODUCT)
	git commit -a -m "Release $(VERSION)" ; true
	git tag $(VERSION) ; true
	git push --all ; true
	python setup.py clean sdist register upload

tests:
	PYTHONPATH=src:$(PYTHONPATH) python tests/$(OS)/all.py

clean:
	echo $(PRODUCT) | xargs python -c 'import sys,os;sys.stdout.write("\n".join(_ for _ in sys.argv[1:] if os.path.exists(_)))' | xargs rm 

check:
	pychecker -100 $(SOURCES)

test:
	python tests/all.py

MANIFEST: $(MANIFEST)
	@echo $(MANIFEST) | xargs -n1 | sort | uniq > $@

README.md: $(LITTERATE)
	$< $< > $@

#EOF
