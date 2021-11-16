# Packages needed on debian:
#    * xsltproc
#    * docbook-xsl-ns (which depends on docbook-xsl-doc-html and docbook5-xml)
#    * libxml2-utils
#

XSL=/usr/share/xml/docbook/stylesheet/docbook-xsl-ns/manpages/docbook.xsl
HXSL=/usr/share/xml/docbook/stylesheet/docbook-xsl-ns/html/docbook.xsl
CONV5XSL="/usr/share/xml/docbook/stylesheet/docbook5/db4-upgrade.xsl"
XP=/usr/bin/xsltproc
OPTIONS=--nonet\
   --param make.year.ranges 1\
   --param make.single.year.ranges 1 \
   --param man.charmap.use.subset 0 \
   --novalid \

all: man

mpd_sima: mpd_sima.1.xml
	xmllint --xinclude --nowarning --noent $< | $(XP) $(OPTIONS) $(XSL) -

mpd_sima.cfg: mpd_sima.cfg.5.xml
	xmllint --xinclude --nowarning --noent $< | $(XP) $(OPTIONS) $(XSL) -

mpd_sima_html:
	xmllint --xinclude --nowarning --noent mpd_sima.1.xml | $(XP) $(HXSL) - > ./mpd_sima.1.html

mpd_sima.cfg_html:
	xmllint --xinclude --nowarning --noent mpd_sima.cfg.5.xml | $(XP) $(HXSL) - > ./mpd_sima.cfg.5.html

man: mpd_sima mpd_sima.cfg

html: simadb_cli_html mpd_sima_html mpd_sima.cfg_html

pdf: mpd-sima.1 mpd-sima.cfg.5
	/usr/bin/man -l -Tps mpd-sima.1 | /usr/bin/ps2pdf - ./mpd_sima.pdf
	/usr/bin/man -l -Tps mpd-sima.cfg.5 | /usr/bin/ps2pdf - ./mpd_sima.cfg.pdf

valid:
	xmllint --noout --valid ./*.xml

clean_mpd_sima:
	rm -rf mpd-sima.1 mpd_sima.1.html

clean_mpd_sima.cfg:
	rm -rf mpd_sima.cfg.5 mpd_sima.cfg.5.html

clean: clean_mpd_sima clean_simadb_cli clean_mpd_sima.cfg
	rm -rf ./*.pdf
