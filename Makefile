DOMAIN = animation-speech
VERSION = 1.2.0
LANGS = fr en
POTFILE = locales/$(DOMAIN).pot
SRCFILES = $(wildcard animation_speech/*.py)
SHFILES  = debian/animation-speech-ctl
TARNAME = $(DOMAIN)-$(VERSION)

DEBFILE = $(DOMAIN)_$(VERSION)_all.deb
RPMFILE = $(DOMAIN)-$(VERSION)-1.noarch.rpm

.PHONY: pot update-po mo stats clean build dist deb rpm release

pot:
	xgettext --language=Python --keyword=_ --output=$(POTFILE) \
		--package-name=$(DOMAIN) --copyright-holder="Rapha" \
		--msgid-bugs-address="" --from-code=UTF-8 $(SRCFILES)
	xgettext --language=Shell --keyword=_ --join-existing --output=$(POTFILE) \
		--from-code=UTF-8 $(SHFILES)

update-po:
	@for lang in $(LANGS); do \
		pofile=locales/$$lang/LC_MESSAGES/$(DOMAIN).po; \
		if [ -f "$$pofile" ]; then \
			echo "Updating $$pofile"; \
			msgmerge --update --no-fuzzy-matching $$pofile $(POTFILE); \
		else \
			echo "Creating $$pofile"; \
			msginit --no-translator --locale=$$lang --input=$(POTFILE) --output=$$pofile; \
		fi; \
	done

mo:
	@for lang in $(LANGS); do \
		pofile=locales/$$lang/LC_MESSAGES/$(DOMAIN).po; \
		mofile=locales/$$lang/LC_MESSAGES/$(DOMAIN).mo; \
		if [ -f "$$pofile" ]; then \
			echo "Compiling $$mofile"; \
			msgfmt -o $$mofile $$pofile; \
		fi; \
	done

stats:
	@for lang in $(LANGS); do \
		pofile=locales/$$lang/LC_MESSAGES/$(DOMAIN).po; \
		if [ -f "$$pofile" ]; then \
			echo "=== $$lang ==="; \
			msgfmt --statistics $$pofile 2>&1; \
		fi; \
	done

build:
	rm -rf .zipapp-build animation-speech.pyz
	mkdir -p .zipapp-build/animation_speech
	cp animation_speech/*.py .zipapp-build/animation_speech/
	printf 'from animation_speech.main import main\nmain()\n' > .zipapp-build/__main__.py
	python3 -m zipapp .zipapp-build -o animation-speech.pyz \
		-p '/usr/bin/env python3'
	rm -rf .zipapp-build

dist: build mo
	rm -rf .dist-build
	mkdir -p .dist-build/$(TARNAME)
	cp animation-speech.pyz .dist-build/$(TARNAME)/animation-speech
	chmod 755 .dist-build/$(TARNAME)/animation-speech
	cp debian/animation-speech-ctl .dist-build/$(TARNAME)/
	chmod 755 .dist-build/$(TARNAME)/animation-speech-ctl
	cp config.yaml .dist-build/$(TARNAME)/
	cp -r config.examples .dist-build/$(TARNAME)/
	cp install.sh .dist-build/$(TARNAME)/
	chmod 755 .dist-build/$(TARNAME)/install.sh
	cp README.md .dist-build/$(TARNAME)/
	for lang in $(LANGS); do \
		mkdir -p .dist-build/$(TARNAME)/locales/$$lang/LC_MESSAGES; \
		cp locales/$$lang/LC_MESSAGES/$(DOMAIN).mo \
		   .dist-build/$(TARNAME)/locales/$$lang/LC_MESSAGES/ 2>/dev/null || true; \
	done
	cd .dist-build && tar czf ../$(TARNAME).tar.gz $(TARNAME)
	rm -rf .dist-build
	@echo ""
	@echo "=== $(TARNAME).tar.gz créé ==="
	@echo ""
	@echo "Installation :"
	@echo "  tar xzf $(TARNAME).tar.gz"
	@echo "  cd $(TARNAME)"
	@echo "  ./install.sh"

deb: build mo
	cd debian && ./build-deb.sh
	@echo ""
	@echo "=== $(DEBFILE) créé ==="

rpm:
	rm -rf .rpm-src-build
	mkdir -p .rpm-src-build/$(TARNAME)/debian
	cp -r animation_speech .rpm-src-build/$(TARNAME)/
	cp -r locales .rpm-src-build/$(TARNAME)/
	cp -r config.examples .rpm-src-build/$(TARNAME)/
	cp debian/animation-speech-ctl .rpm-src-build/$(TARNAME)/debian/
	cp animation-speech.spec README.md LICENSE .rpm-src-build/$(TARNAME)/
	cd .rpm-src-build && tar czf $(TARNAME).tar.gz $(TARNAME)
	mkdir -p $(HOME)/rpmbuild/{SOURCES,SPECS}
	cp .rpm-src-build/$(TARNAME).tar.gz $(HOME)/rpmbuild/SOURCES/
	cp animation-speech.spec $(HOME)/rpmbuild/SPECS/
	rm -rf .rpm-src-build
	rpmbuild -bb $(HOME)/rpmbuild/SPECS/animation-speech.spec
	cp $(HOME)/rpmbuild/RPMS/noarch/$(RPMFILE) .
	@echo ""
	@echo "=== $(RPMFILE) créé ==="

release: dist deb
	@echo ""
	@echo "=== Upload des assets sur la release v$(VERSION) ==="
	@echo ""
	gh release upload v$(VERSION) $(TARNAME).tar.gz --clobber
	gh release upload v$(VERSION) $(DEBFILE) --clobber
	@if [ -f "$(RPMFILE)" ]; then \
		gh release upload v$(VERSION) $(RPMFILE) --clobber; \
	else \
		echo "⚠ RPM non trouvé (rpmbuild non disponible ?) — ignoré"; \
	fi
	@echo ""
	@echo "=== Assets uploadés sur v$(VERSION) ==="
	gh release view v$(VERSION) --json assets --jq '.assets[].name'

clean:
	rm -f locales/*/LC_MESSAGES/$(DOMAIN).mo
	rm -f $(POTFILE)
	rm -f animation-speech.pyz
	rm -f $(TARNAME).tar.gz
	rm -f $(DEBFILE)
	rm -f $(RPMFILE)
