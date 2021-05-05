import pywikibot
import re

Namespace = pywikibot.site.Namespace

def log(info, format_spec, *args):
	print('LOG', info.page_name, format_spec.format(*args), sep='|')

def stringify(params):
	return '|'.join(['='.join(p) for p in sorted(params.items())])

Replace_With_Dash = re.compile('[^0-9a-z]+')
Translation_Table = str.maketrans({
	'ä': 'ae',
	'ö': 'oe',
	'ü': 'ue',
	'ß': 'ss',
	'â': 'a',
	'à': 'a',
	'é': 'e',
	'ô': 'o',
	'\u2019': None, # apostrophe (right single quotation mark)
})

def title2url(title):
	url = title.lower().translate(Translation_Table)
	url = Replace_With_Dash.sub('-', url)

	if url[0] == '-':
		url = url[1:]
	if url[-1] == '-':
		url = url[:-1]

	return url

EnDash = '\u2013'
Months = {
	'Januar':    1, 'Jan.':  1,
	'Februar':   2, 'Feb.':  2,
	'März':      3, 'Mär.':  3,
	'April':     4, 'Apr.':  4,
	'Mai':       5,
	'Juni':      6, 'Jun.':  6,
	'Juli':      7, 'Jul.':  7,
	'August':    8, 'Aug.':  8,
	'September': 9, 'Sep.':  9,
	'Oktober':  10, 'Okt.': 10,
	'November': 11, 'Nov.': 11,
	'Dezember': 12, 'Dez.': 12,
}
Month_Days = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
Date_Pattern = re.compile('^(?:\\{\\{0\\}\\})?([1-9][0-9]?)\\.(?: |&nbsp;)([A-Z][a-zä]+\\.?) +([12][0-9]{3})')
Double_Episode_Date = ('27. September und 4. Oktober 2015', '2015-09-27')
Special_Dates = {
	('Polizeiruf 110: Kreise', 'NF-DATUM'): Double_Episode_Date,
	('Polizeiruf 110: Wendemanöver', 'Erstausstrahlung'): Double_Episode_Date,
	('Polizeiruf 110: Grenzgänger', 'VG-DATUM'): Double_Episode_Date,
}
Alternate_Infobox_Dates = {
}
def parse_date_extra(info, param, extra):
	return False

def parse_date(date, info, param):
	m = Date_Pattern.match(date)
	if m is None:
		special = Special_Dates.get((info.page_name, param))
		if special:
			if date == special[0]:
				return special[1]
		elif date in ('', EnDash) and param in ('VG-DATUM', 'NF-DATUM'):
			return ''
		log(info, 'Cannot parse date|{}={}|', param, date)
		return ''
	extra = date[m.end():]
	if extra and not parse_date_extra(info, param, extra):
		log(info, 'Extra text after date|{}={}|', param, date)

	day, month, year = m.groups()
	day, month, year = int(day), Months.get(month, 0), int(year)

	if month == 0:
		log(info, 'Invalid month|{}={}|', param, date)
	elif day > Month_Days[month - 1]:
		log(info, 'Invalid day|{}={}|', param, date)

	return '{}-{:02}-{:02}'.format(year, month, day)

Alternate_Titles = {
	'Polizeiruf 110: In Erinnerung an …': '"In Erinnerung an …"',
}
Episode_Number_Pattern = re.compile('^[1-9][0-9]*')
PageName_Suffix_Pattern = re.compile('^ \\((?:[12][0-9]{3}|Film)\\)$')

def get_episode_name(name):
	if name.startswith('Polizeiruf 110: '):
		name = name[16:]
	if name.endswith(')'):
		i = name.find('(')
		if i > 1 and PageName_Suffix_Pattern.match(name[i-1:]):
			name = name[:i-1]
	return name

def check_title(info, template, title):
	title = title.replace('&nbsp;', ' ')
	if title == info.episode_name:
		return
	if title == Alternate_Titles.get(info.page_name):
		return
	if title == 'Polizeiruf 110: ' + info.episode_name:
		return
	log(info, 'Mismatched {} title|{}|', template, title)

class TatortInfo(object):
	def __init__(self, page_name):
		self.page_name = page_name
		self.episode_name = get_episode_name(page_name)
		self.prev_episode = None
		self.next_episode = None
		self.imdb = None
		self.episode_number = None
		self.infobox_title = None
		self.infobox_date = None
		self.double_episode = False

def do_folgenleiste(info, params):
	if info.prev_episode is not None:
		log(info, 'Skipping duplicate Folgenleiste')
		return

	info.prev_episode = params.pop('VG', '')
	info.next_episode = params.pop('NF', '')
	info.prev_ep_page = params.pop('VG-ARTIKEL', None)
	info.next_ep_page = params.pop('NF-ARTIKEL', None)
	info.prev_ep_date = parse_date(params.pop('VG-DATUM', ''), info, 'VG-DATUM')
	info.next_ep_date = parse_date(params.pop('NF-DATUM', ''), info, 'NF-DATUM')
	if params:
		log(info, 'Extraneous Folgenleiste parameters|{}|', stringify(params))

def do_imdb(info, params):
	if info.imdb is not None:
		if info.imdb == params:
			log(info, 'Skipping duplicate IMDb')
		else:
			log(info, 'Skipping different IMDb')
		return

	title = params.get('2')
	if title is not None:
		check_title(info, 'IMDb', title)

	info.imdb = params

def set_infobox_title(info, title):
	if not info.infobox_title:
		info.infobox_title = title
		return True
	if title:
		log(info, 'Previous Infobox already specified episode title')
	return False

def get_infobox_title(info, params):
	title = ''
	title_param = None

	for p in ('OT', 'Originaltitel', 'DT', 'Titel'):
		v = params.get(p)
		if not v:
			continue
		i = v.find('[')
		if i >= 0:
			v = v[:i].rstrip()
		i = v.find('<')
		if i >= 0:
			v = v[:i].rstrip()
		if not title:
			title = v
			title_param = p
		elif title != v:
			log(info, '{} and {} are different', p, title_param)

	return set_infobox_title(info, title)

def set_infobox_date(info, date):
	if not info.infobox_date:
		info.infobox_date = date
		return True
	if date:
		log(info, 'Previous Infobox already specified episode date')
	return False

def get_infobox_date(info, params):
	date = ''
	date_param = None

	for p in ('EAS', 'Erstausstrahlung', 'EASDE', 'Erstausstrahlung_DE'):
		v = params.get(p)
		if not v:
			continue
		v = parse_date(v, info, p)
		if not v:
			continue
		alt = Alternate_Infobox_Dates.get(info.page_name)
		if alt:
			if v == alt[0]:
				v = alt[1]
			else:
				log(info, 'Unexpected Infobox date|{}|{}|', v, alt[0])
		if not date:
			date = v
			date_param = p
			if p[-2:] == 'DE':
				log(info, 'Use EAS/Erstausstrahlung instead of {}', p)
		elif date == v:
			log(info, 'Duplicate Infobox date|{}|{}', date_param, p)
		else:
			log(info, '{} and {} are different', p, date_param)

	return set_infobox_date(info, date)

def check_episode_number(info, ep):
	m = Episode_Number_Pattern.match(ep)
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

def set_episode_number(info, ep):
	if info.episode_number is None:
		info.episode_number = ep
		return True
	log(info, 'Previous Infobox already specified episode number')
	return False

def do_infobox_episode(info, params):
	series = params.get('Serie', '')
	if series == 'Polizeiruf 110':
		set_episode_number(info, params.get('Episode', ''))
	elif series:
		log(info, 'Skipping Infobox for another series|{}|', series)
		return

	if 'Serienlogo' in params:
		log(info, 'Should remove Infobox parameter Serienlogo')

	get_infobox_title(info, params)
	get_infobox_date(info, params)

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
	templates = {
		'Folgenleiste Polizeiruf-110-Folgen': do_folgenleiste,
		'IMDb': do_imdb,
		'Infobox Episode': do_infobox_episode,
		'Medienbox': do_infobox_episode,
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
			check_title(info, 'Infobox', info.infobox_title)
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

if __name__ == '__main__':
	main()
