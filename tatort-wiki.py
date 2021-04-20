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

	'Jänner':    1, # Tatort: Die Faust (Parameter 'EAS' in Vorlage 'Infobox Episode')
}
Month_Days = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
Date_Pattern = re.compile('^(?:\\{\\{0\\}\\})?([1-9][0-9]?)\\.(?: |&nbsp;)([A-Z][a-zä]+\\.?) ([12][0-9]{3})')
Double_Episode_Date = ('29. November und 6. Dezember 2020', '2020-11-29')
Special_Dates = {
	('Tatort: Borowski und die Frau am Fenster', 'Erstausstrahlung'): ('2. Oktober [[2011]]', '2011-10-02'),
	('Tatort: Die Ferien des Monsieur Murot', 'NF-DATUM'): Double_Episode_Date,
	('Tatort: In der Familie', 'Erstausstrahlung'): Double_Episode_Date,
	('Tatort: Es lebe der König!', 'VG-DATUM'): Double_Episode_Date,
}
Alternate_Infobox_Dates = {
	'Tatort: Exklusiv!': ('1969-10-26', '1971-07-11'),
	'Zahn um Zahn (1985)': ('1985-10-10', '1987-12-27'),
	'Zabou (Film)': ('1987-03-05', '1990-07-22'),
	'Tatort: Mord hinterm Deich': ('1996-12-25', '1997-06-08'),
	'Tatort: Passion': ('1999-11-17', '2000-07-30'),
	'Tatort: Time-Out': ('2001-09-23', '2002-12-22'),
	'Tatort: Seenot': ('2008-01-13', '2008-03-24'),
	'Tatort: Der Polizistinnenmörder': ('2010-01-03', '2010-01-17'),
}
def parse_date_extra(info, param, extra):
	if extra == ' (nur ORF)':
		if param == 'VG-DATUM':
			info.prev_orf = True
			return True
		if param == 'NF-DATUM':
			info.next_orf = True
			return True
	return False

def parse_date(date, info, param):
	m = Date_Pattern.match(date)
	if m is None:
		special = Special_Dates.get((info.page_name, param))
		if special:
			if date == special[0]:
				return special[1]
		elif date in ('', EnDash) and param in ('VG-DATUM', 'NF-DATUM'):
			return EnDash
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
	'Tatort: Acht, neun – aus': 'Acht, neun – aus!',
	'Tatort: Aus der Traum (2006)': 'Aus der Traum …',
	'Tatort: Die schlafende Schöne': 'Die Schlafende Schöne',
	'Tatort: Laura mein Engel': 'Laura, mein Engel',
	'Tatort: Romeo und Julia': 'Romeo & Julia',
	'Tatort: Stirb und werde': 'Stirb und Werde',
	'Tatort: Tote Taube in der Beethovenstraße': 'Kressin: Tote Taube in der Beethovenstraße',
	'Tatort: … es wird Trauer sein und Schmerz': '... es wird Trauer sein und Schmerz',
}
Episode_Number_Pattern = re.compile('^[1-9][0-9]*')
PageName_Suffix_Pattern = re.compile('^ \\((?:[12][0-9]{3}|Film)\\)$')

def get_episode_name(name):
	if name.startswith('Tatort: '):
		name = name[8:]
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
	if title == 'Tatort: ' + info.episode_name:
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
		self.tatort_fans = None
		self.tatort_folge = None
		self.tatort_fundus = None
		self.double_episode = False
		self.orf = False

def do_folgenleiste(info, params):
	if info.prev_episode is not None:
		log(info, 'Skipping duplicate Folgenleiste')
		return

	info.prev_orf = False
	info.next_orf = False
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
		info.sortkey = (ep, 0)
		return True
	if suffix == 'a':
		info.sortkey = (ep, 1)
		info.orf = True
		return True
	if suffix == 'b':
		info.sortkey = (ep, 2)
		info.orf = True
		return True
	if suffix == ', ' + str(ep + 1):
		info.sortkey = (ep, 0)
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
	if series == 'Tatort':
		set_episode_number(info, params.get('Episode', ''))
	elif series:
		log(info, 'Skipping Infobox for another series|{}|', series)
		return

	if 'Serienlogo' in params:
		log(info, 'Should remove Infobox parameter Serienlogo')

	get_infobox_title(info, params)
	get_infobox_date(info, params)

def do_infobox_film(info, params):
	if not get_infobox_title(info, params):
		return
	if info.infobox_title == 'Tschiller: Off Duty':
		set_infobox_date(info, '2018-07-08')
		set_episode_number(info, '1062')

def do_tatort_fans(info, params):
	if info.tatort_fans is None:
		info.tatort_fans = [params]
	else:
		info.tatort_fans.append(params)

def do_tatort_folge(info, params):
	if info.tatort_folge is None:
		info.tatort_folge = [params]
	else:
		info.tatort_folge.append(params)

def do_tatort_fundus(info, params):
	if info.tatort_fundus is None:
		info.tatort_fundus = [params]
	else:
		info.tatort_fundus.append(params)

Tatort_Fans_URL_Map = {}
Tatort_Folge_URL_Map = {}
Tatort_Fundus_URL_Map = {}

def load_url_map(filename, lookup):
	with open(filename) as f:
		for line in f:
			ep, url = line.split('|', maxsplit=1)
			lookup[ep] = url[:-1]

def mismatched_url(info, url, expected_url, template):
	log(info, 'Mismatched Tatort-{} URL|{}|{}|{}|', template, info.episode_number, url, expected_url)

Special_Tatort_Fans_Numbers = {
	'Tatort: Angriff auf Wache 08': '1005', # instead of 1105
	'Tatort: Einmal täglich': '456', # instead of 457
	'Tatort: Nachtgeflüster': '674', # instead of 675
}
Special_Tatort_Fundus_Numbers = {
	'Tatort: Wer jetzt allein ist': 'tatort-folge-1059', # instead of 1059
}
def check_tatort_nr(info, params, template, lookup):
	n = params.pop('Nr', None)
	if not n:
		log(info, 'Missing Tatort-{} episode number', template)
		return
	ep = lookup.get(info.page_name, info.episode_number)
	if n == ep:
		return
	if len(n) == 3 and n[0] == '0' and n.lstrip('0') == ep:
		return
	log(info, 'Mismatched Tatort-{} episode number|{}|{}|', template, n, ep)

def default_tatort_template_title(page_name):
	return page_name[8:] if page_name.startswith('Tatort: ') else page_name

def check_tatort_fans(info):
	default_title = default_tatort_template_title(info.page_name)
	expected_url = Tatort_Fans_URL_Map.get(info.episode_number, title2url(info.episode_name))

	for params in info.tatort_fans:
		check_tatort_nr(info, params, 'Fans', Special_Tatort_Fans_Numbers)

		url = params.pop('Url', '').lower()
		if not url:
			log(info, 'Missing Tatort-Fans URL')
		elif url != expected_url:
			mismatched_url(info, url, expected_url, 'Fans')

		title = params.pop('Titel', None)
		if title is not None:
			check_title(info, 'Tatort-Fans', title)
		elif info.episode_name != default_title:
			log(info, 'Should specify Tatort-Fans title')

		if params:
			log(info, 'Extraneous Tatort-Fans parameters|{}|', stringify(params))

def check_tatort_folge(info):
	default_title = default_tatort_template_title(info.page_name)
	expected_url = Tatort_Folge_URL_Map.get(info.episode_number, title2url(info.episode_name) + '-')
	prev_url = None

	for params in info.tatort_folge:
		url = params.pop('Url', None)
		if not url:
			log(info, 'Missing Tatort-Folge URL')
		elif not (len(url) > 3
			and 49 <= ord(url[-3]) <= 50
			and 48 <= ord(url[-2]) <= 57
			and 48 <= ord(url[-1]) <= 57
		):
			log(info, 'Invalid Tatort-Folge URL suffix|{}|', url)
		else:
			if url[0] == '/':
				url = url[1:]
			if not prev_url:
				prev_url = url
			elif url != prev_url:
				log(info, 'Tatort-Folge with different URL|{}|{}|', url, prev_url)
			url = url[:-3]
			if url != expected_url:
				mismatched_url(info, url, expected_url, 'Folge')

		title = params.pop('Titel', None)
		if title is not None:
			check_title(info, 'Tatort-Folge', title)
		elif info.episode_name != default_title:
			log(info, 'Should specify Tatort-Folge title')

		if params:
			log(info, 'Extraneous Tatort-Folge parameters|{}|', stringify(params))

	info.tatort_folge = prev_url

def check_tatort_fundus(info):
	default_title = default_tatort_template_title(info.page_name)
	expected_url = Tatort_Fundus_URL_Map.get(info.episode_number, title2url(info.episode_name))

	for params in info.tatort_fundus:
		year = params.pop('Jahr', None)
		if not year:
			log(info, 'Missing Tatort-Fundus year')
		elif year != info.infobox_date[:4]:
			log(info, 'Mismatched Tatort-Fundus year|{}|{}|', year, info.infobox_date[:4])

		check_tatort_nr(info, params, 'Fundus', Special_Tatort_Fundus_Numbers)

		url = params.pop('Url', None)
		if not url:
			log(info, 'Missing Tatort-Fundus URL')
		else:
			url_parts = url.split('/')
			num_parts = len(url_parts)
			if num_parts != 1 and num_parts != 2:
				log(info, 'Invalid Tatort-Fundus URL|{}|', url)
			else:
				url = url_parts[0].lower().replace('_', '-')
				if url != expected_url:
					mismatched_url(info, url, expected_url, 'Fundus')

		title = params.pop('Titel', None)
		if url and num_parts == 2:
			if not (title and title.startswith(info.episode_name + ': ')):
				log(info, 'Invalid Tatort-Fundus subpage title|{}|', title)
			else:
				url = url_parts[1]
				subpage_url = title2url(title[len(info.episode_name) + 2:])
				if url != subpage_url:
					log(info, 'Mismatched Tatort-Fundus subpage URL|{}|{}|', url, subpage_url)
		elif title is not None:
			check_title(info, 'Tatort-Fundus', title)
		elif info.episode_name != default_title:
			log(info, 'Should specify Tatort-Fundus title')

		if params:
			log(info, 'Extraneous Tatort-Fundus parameters|{}|', stringify(params))

def check_attr(info, attr, value):
	if getattr(info, attr) != value:
		log(info, 'Mismatched {}|{}|{}|', attr, getattr(info, attr), value)

def check_link(info, attr, name):
	link = getattr(info, attr + '_ep_page') or 'Tatort: ' + getattr(info, attr + '_episode')
	if link != name and link != name.replace(' ', '_'):
		log(info, 'Mismatched {}_ep_page|{}|{}|', attr, link, name)

def ep2str(ep):
	n, x = ep
	ep = str(n)
	return ep + chr(96 + x) if x else ep

def get_pages():
	site = pywikibot.Site(code='de')
	return pywikibot.Page(site, 'Folgenleiste Tatort-Folgen', ns=Namespace.TEMPLATE).getReferences(
		only_template_inclusion=True, namespaces=(Namespace.MAIN,))

def main():
	load_url_map('tatort-fans-url-map.txt', Tatort_Fans_URL_Map)
	load_url_map('tatort-folge-url-map.txt', Tatort_Folge_URL_Map)
	load_url_map('tatort-fundus-url-map.txt', Tatort_Fundus_URL_Map)

	templates = {
		'Folgenleiste Tatort-Folgen': do_folgenleiste,
		'IMDb': do_imdb,
		'Infobox Episode': do_infobox_episode,
		'Infobox Film': do_infobox_film,
		'Medienbox': do_infobox_episode,
		'Tatort-Fans': do_tatort_fans,
		'Tatort-Folge': do_tatort_folge,
		'Tatort-Fundus': do_tatort_fundus,
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
			log(info, 'Missing Tatort Infobox')
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
		if info.tatort_fans:
			check_tatort_fans(info)
		elif not info.orf:
			log(info, 'Missing Tatort-Fans')
		if info.tatort_folge:
			check_tatort_folge(info)
		elif not info.orf:
			log(info, 'Missing Tatort-Folge')
		if info.tatort_fundus:
			check_tatort_fundus(info)

		info_list.append(info)

	for name, count in sorted(categories.items()):
		print('CAT', '{:5}'.format(count), name, sep='|')

	info_list.sort(key=lambda info: info.sortkey)
	next_ep = (1, 0)
	prev = None

	for info in info_list:
		ep = info.sortkey
		if ep != next_ep:
			log(info, 'Unexpected episode number|{}|{}', ep2str(ep), ep2str(next_ep))
		elif prev:
			if prev.orf != info.prev_orf:
				log(info, '{}xpected " (nur ORF)" after prev_ep_date', 'E' if prev.orf else 'Une')
			check_attr(info, 'prev_episode', prev.episode_name)
			check_attr(info, 'prev_ep_date', prev.infobox_date)
			check_link(info, 'prev', prev.page_name)

			if info.orf != prev.next_orf:
				log(prev, '{}xpected " (nur ORF)" after next_ep_date', 'E' if info.orf else 'Une')
			check_attr(prev, 'next_episode', info.episode_name)
			check_attr(prev, 'next_ep_date', info.infobox_date)
			check_link(prev, 'next', info.page_name)
		else:
			check_attr(info, 'prev_episode', EnDash)
			check_attr(info, 'prev_ep_date', EnDash)

		if info.tatort_folge:
			print(info.episode_number, info.infobox_date, info.episode_name, info.tatort_folge, sep='|')

		if info.double_episode:
			ep = (ep[0] + 1, 0)

		next_ep = (ep[0], ep[1] + 1) if info.next_orf else (ep[0] + 1, 0)
		prev = info

	if prev:
		check_attr(prev, 'next_episode', EnDash)
		check_attr(prev, 'next_ep_date', EnDash)

if __name__ == '__main__':
	main()
