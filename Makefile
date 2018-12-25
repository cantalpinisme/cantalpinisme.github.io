
NOW := `date "+%FT%H%M"`
BASE := http://cantalpinisme.eu/
# BASE := https://xldb2017.isima.fr/
# BASE := http://localhost:8000/
# DEPLOY := xldb://var/www/clients/client0/web5/web
DEPLOY := www0059@195.221.122.109:/www

DATADIR := data
TEMPLATES := templates
BUILDER = python -O tools/render.py -b $(BASE) --data-dir $(DATADIR) --templates-dir $(TEMPLATES) --lang fr_FR.utf-8
JSMIN := /usr/bin/closure-compiler --compilation_level SIMPLE_OPTIMIZATIONS --third_party
#JSMIN := slimit -m -t
# JSMIN := cat

IMAGES := \
  img/affiche.jpg \
  img/casino-salle-grand-jeux.jpg \
  img/casino-salle-theatre-2.jpg \
  img/casino-salle-theatre.jpg \
  img/clermont.png \
  img/icalendar.png \
  img/logo-ame.jpg \
  img/logo-ffcam.png \
  img/rss.png \
  img/logo.png \
  img/banner0.jpg \
  img/banner1.jpg \
  img/banner2.jpg \
  img/banner3.jpg \
  img/banner4.jpg \
  img/banner5.jpg \
  img/favicon.png \
  img/goulotte.jpg \
  img/sommet-bataillouze.jpg

SCRIPTS := scripts/map.js

STYLES := styles/base.css \
		  styles/print.css

PAGES := \
	index.html \
	news.html \
	news.atom \
	dates.ics \
	info.html \
	site.html \
	comites.html \
	program.html \
	credits.html \
	register.html

# keynotes.html \
# papers.html \


SITEFILES := $(STYLES) $(FILES) $(IMAGES) $(SCRIPTS) .htaccess $(PAGES)


.PHONY: site
site: $(addprefix build/, $(SITEFILES))
	chmod -R a+r build
	chmod -R a+X build

.PHONY: install
install: site
	rsync -a --delete build/ $(DEPLOY)

.PHONY: clean
clean:
	rm -rf build
	rm -rf .sass-cache

build/%.atom: $(DATADIR)/news.yml
	mkdir -p $(@D)
	$(BUILDER) -t $*.atom >| $@

build/%.ics: $(DATADIR)/dates.yml
	mkdir -p $(@D)
	$(BUILDER) -t $*.ics >| $@

build/%.html: $(TEMPLATES)/%.html $(TEMPLATES)/page-xhtmlrdfa.jinja $(DATADIR)/*.yml
	mkdir -p $(@D)
	$(BUILDER) -t $*.html >| $@

build/styles/%.css: styles/%.scss
	mkdir -p $(@D)
	sass -t compressed $< >| $@

# build/favicon.ico: img/logo.png
# 	mkdir -p $(@D)
# 	convert -resize 32x32 $< $@
#
# build/favicon.png: img/logo.png
# 	mkdir -p $(@D)
# 	convert -resize 32x32 -negate $< $@

build/img/%: img/%
	mkdir -p $(@D)
	cp -a $< $@

build/files/%: files/%
	mkdir -p $(@D)
	cp -a $< $@

build/scripts/%.js: scripts/%.coffee
	mkdir -p $(@D)
	coffee -p $< | $(JSMIN) >| $@

build/styles/base.css: styles/*.scss

build/cfpdemo.%.pdf: files/cfp-%.pdf
	cp -a $< $@

build/cfpdemo.pdf.%: build/cfpdemo.%.pdf
	cp -a $< $@

build/.htaccess: files/htaccess
	cp -a $< $@



