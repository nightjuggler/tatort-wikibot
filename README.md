## tatort-wikibot

* `python3 tatort-wiki.py > tatort.txt` (requires [pywikibot](https://www.mediawiki.org/wiki/Manual:Pywikibot))
* `grep ^LOG tatort.txt > tatort.log`
* `grep -v ^LOG tatort.txt > tatort-wiki-episodes.txt`
* `python3 tatort.py tatort_fetch > tatort-html-episodes.txt`
* `python3 tatort.py tatort_diff`

* `python3 tatort.py fans_fetch > tatort-fans-episodes.txt`
* `python3 tatort.py fans_urlmap | diff tatort-fans-url-map.txt -`
* `python3 tatort.py tatort_urlmap | diff tatort-folge-url-map.txt -`
