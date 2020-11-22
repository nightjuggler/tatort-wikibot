## tatort-wikibot

* `python3 tatort-wiki.py > tatort.txt` (requires [pywikibot](https://www.mediawiki.org/wiki/Manual:Pywikibot))
* `grep ^LOG tatort.txt > tatort.log`
* `grep -v ^LOG tatort.txt | grep -v ^CAT > tatort-wiki-episodes.txt`
* `python3 tatort.py fetch > tatort-html-episodes.txt`
* `python3 tatort.py diff`

