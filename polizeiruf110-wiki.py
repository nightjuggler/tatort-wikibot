import pywikibot
import re
import tatort_wiki_lib as TW

Namespace = pywikibot.site.Namespace
log = TW.log

Double_Episode_Date = ('27. September und 4. Oktober 2015', '2015-09-27')
TW.Special_Dates = {
	('Polizeiruf 110: Kreise', 'NF-DATUM'): Double_Episode_Date,
	('Polizeiruf 110: Wendemanöver', 'Erstausstrahlung'): Double_Episode_Date,
	('Polizeiruf 110: Grenzgänger', 'VG-DATUM'): Double_Episode_Date,
}
TW.Series = 'Polizeiruf 110'
TW.Series_Prefix = 'Polizeiruf 110: '
TW.Alternate_Titles = {
	'Polizeiruf 110: In Erinnerung an …': '"In Erinnerung an …"',
}

class TatortInfo(object):
	def __init__(self, page_name):
		self.page_name = page_name
		self.episode_name = TW.get_episode_name(page_name)
		self.prev_episode = None
		self.next_episode = None
		self.imdb = None
		self.episode_number = None
		self.infobox_title = None
		self.infobox_date = None
		self.double_episode = False

def check_episode_number(info, ep):
	m = TW.Episode_Number_Pattern.match(ep)
	if not m:
		return False

	i = m.end()
	suffix = ep[i:]
	ep = int(ep[:i])

	if suffix == '':
		info.sortkey = ep
		return True
	if suffix == ', ' + str(ep + 1):
		info.sortkey = ep
		info.episode_number = str(ep)
		info.double_episode = True
		return True

	return False

TW.Infobox_Series_Params.extend((
	('Serie_Link',    False, 'Polizeiruf 110'),
	('Episodenliste', True,  'Liste der Polizeiruf-110-Folgen'),
))

URL_Prefix = 'www.daserste.de/unterhaltung/krimi/polizeiruf-110/sendung/'
URL_Suffix_Pattern = re.compile('^(?:[0-9]{4}/)?([0-9a-z]+(?:-[0-9a-z]+)*-?[0-9]{3})\\.html$')

def get_urls(info, page):
	urls = []
	for url in page.extlinks():
		if url.startswith('https://'):
			url = url[8:]
		elif url.startswith('http://'):
			url = url[7:]
		else:
			log(info, 'Unexpected URL protocol|{}', url)
			continue
		if not url.startswith(URL_Prefix):
			continue
		url = url[len(URL_Prefix):]
		m = URL_Suffix_Pattern.match(url)
		if not m:
			log(info, 'Unexpected URL suffix|{}', url)
			continue
		urls.append(m.group(1))
	info.url = ','.join(urls)

def check_attr(info, attr, value):
	if getattr(info, attr) != value:
		log(info, 'Mismatched {}|{}|{}|', attr, getattr(info, attr), value)

def check_link(info, attr, name):
	link = getattr(info, attr + '_ep_page') or 'Polizeiruf 110: ' + getattr(info, attr + '_episode')
	if link != name and link != name.replace(' ', '_'):
		log(info, 'Mismatched {}_ep_page|{}|{}|', attr, link, name)

def get_pages():
	site = pywikibot.Site(code='de')
	return pywikibot.Page(site, 'Folgenleiste Polizeiruf-110-Folgen', ns=Namespace.TEMPLATE).getReferences(
		only_template_inclusion=True, namespaces=(Namespace.MAIN,))

def main():
	TW.Infobox_Stats.init()

	templates = {
		'Folgenleiste Polizeiruf-110-Folgen': TW.do_folgenleiste,
		'IMDb': TW.do_imdb,
		'Infobox Episode': TW.do_infobox_episode,
		'Medienbox': TW.do_medienbox,
	}
	categories = {}
	info_list = []
	main_ns = Namespace.MAIN

	for page in get_pages():
		info = TatortInfo(page.title())

		ns = page.namespace()
		if ns.id != main_ns:
			log(info, 'Not in the main namespace|{}|', ns.canonical_name)
			continue

		for cat in page.categories():
			name = cat.title()
			categories[name] = categories.get(name, 0) + 1

		for template, params in page.raw_extracted_templates:
			do_template = templates.get(template)
			if do_template:
				do_template(info, params)

		ep = info.episode_number
		if ep is None:
			log(info, 'Missing Polizeiruf 110 Infobox')
			continue
		if not ep:
			log(info, 'Missing episode number')
			continue
		if not check_episode_number(info, ep):
			log(info, 'Invalid episode number|{}|', ep)
			continue

		if info.infobox_title:
			TW.check_title(info, 'Infobox', info.infobox_title)
		else:
			log(info, 'Missing episode title')
		if not info.infobox_date:
			log(info, 'Missing episode date')
			continue
		if info.prev_episode is None:
			log(info, 'Missing Folgenleiste')
			continue

		if info.imdb is None:
			log(info, 'Missing IMDb')

		get_urls(info, page)

		info_list.append(info)

	for name, count in sorted(categories.items()):
		print('CAT', '{:5}'.format(count), name, sep='|')

	info_list.sort(key=lambda info: info.sortkey)
	next_ep = 1
	prev = None

	for info in info_list:
		ep = info.sortkey
		if ep != next_ep:
			log(info, 'Unexpected episode number|{}|{}', ep, next_ep)
		elif prev:
			check_attr(info, 'prev_episode', prev.episode_name)
			check_attr(info, 'prev_ep_date', prev.infobox_date)
			check_link(info, 'prev', prev.page_name)

			check_attr(prev, 'next_episode', info.episode_name)
			check_attr(prev, 'next_ep_date', info.infobox_date)
			check_link(prev, 'next', info.page_name)
		else:
			check_attr(info, 'prev_episode', '')
			check_attr(info, 'prev_ep_date', '')

		if info.double_episode:
			print(ep, info.infobox_date, info.episode_name + ' (1)', info.url, sep='|')
			ep += 1
			print(ep, info.infobox_date, info.episode_name + ' (2)', info.url, sep='|')
		else:
			print(info.episode_number, info.infobox_date, info.episode_name, info.url, sep='|')

		next_ep = ep + 1
		prev = info

	if prev:
		check_attr(prev, 'next_episode', '')
		check_attr(prev, 'next_ep_date', '')

	TW.Infobox_Stats.write('polizeiruf110-infobox-stats.txt')

if __name__ == '__main__':
	main()
