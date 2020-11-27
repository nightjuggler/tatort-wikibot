import pywikibot
import re

Namespace = pywikibot.site.Namespace

def log(info, format_spec, *args):
	print('LOG', info.page_name, format_spec.format(*args), sep='|')

def stringify(params):
	return '|'.join(['='.join(p) for p in sorted(params.items())])

ORF_Episodes = {
	168: (
		('1985-05-19', 'Fahrerflucht'),
	),
	171: (
		('1985-09-08', 'Des Glückes Rohstoff'),
	),
	176: (
		('1986-01-12', 'Strindbergs Früchte'),
	),
	178: (
		('1986-03-02', 'Das Archiv'),
	),
	181: (
		('1986-06-13', 'Die Spieler'),
	),
	184: (
		('1986-08-24', 'Alleingang'),
	),
	186: (
		('1986-10-12', 'Der Schnee vom vergangenen Jahr'),
	),
	187: (
		('1986-12-18', 'Der Tod des Tänzers'),
	),
	188: (
		('1987-01-11', 'Die offene Rechnung'),
	),
	192: (
		('1987-04-25', 'Superzwölfer'),
	),
	199: (
		('1987-12-08', 'Atahualpa'),
		('1987-12-19', 'Flucht in den Tod'),
	),
	218: (
		('1989-05-21', 'Geld für den Griechen'),
	),
}
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
	'Juni.':     6, # Tatort: Durchgedreht (Parameter 'VG-DATUM' in Vorlage 'Folgenleiste Tatort-Folgen')
}
Month_Days = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
Date_Pattern = re.compile('^(?:\\{\\{0\\}\\})?([1-9][0-9]?)\\.(?: |&nbsp;)([A-Z][a-zä]+\\.?) ([12][0-9]{3})')
Special_Dates = {
	('Tatort: Taxi nach Leipzig (1970)', 'VG-DATUM'): (EnDash, EnDash),
	('Tatort: Borowski und die Frau am Fenster', 'Erstausstrahlung'): ('2. Oktober [[2011]]', '2011-10-02'),
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
			info.prev_ep_orf = True
			return True
		if param == 'NF-DATUM':
			info.next_ep_orf = True
			return True
	return False

def parse_date(date, info, param):
	m = Date_Pattern.match(date)
	if m is None:
		special = Special_Dates.get((info.page_name, param))
		if special and date == special[0]:
			return special[1]
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
	'Tatort: Acht, neun – aus': 'Acht, Neun – aus!',
	'Tatort: Aus der Traum (2006)': 'Aus der Traum …',
	'Tatort: Die schlafende Schöne': 'Die Schlafende Schöne',
	'Tatort: Laura mein Engel': 'Laura, mein Engel',
	'Tatort: Romeo und Julia': 'Romeo & Julia',
	'Tatort: Stirb und werde': 'Stirb und Werde',
	'Tatort: Tote Taube in der Beethovenstraße': 'Kressin: Tote Taube in der Beethovenstraße',
	'Tatort: … es wird Trauer sein und Schmerz': '... es wird Trauer sein und Schmerz',
}
Episode_Number_Pattern = re.compile('^[1-9][0-9]*$')
PageName_Suffix_Pattern = re.compile('^ \\([ 0-9A-Za-z]+\\)$')

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

def do_folgenleiste(info, params):
	if info.prev_episode is not None:
		log(info, 'Skipping duplicate Folgenleiste')
		return

	info.prev_episode = params.get('VG', '')
	info.next_episode = params.get('NF', '')
	info.prev_ep_orf = False
	info.next_ep_orf = False
	info.prev_ep_date = parse_date(params.get('VG-DATUM', ''), info, 'VG-DATUM')
	info.next_ep_date = parse_date(params.get('NF-DATUM', ''), info, 'NF-DATUM')

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
		elif date != v:
			log(info, '{} and {} are different', p, date_param)

	return set_infobox_date(info, date)

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

	get_infobox_title(info, params)
	get_infobox_date(info, params)

def do_infobox_film(info, params):
	if not get_infobox_title(info, params):
		return
	if info.infobox_title == 'Tschiller: Off Duty':
		set_infobox_date(info, '2018-07-08')
		set_episode_number(info, '1062')

def default_tatort_template_title(page_name):
	if page_name.startswith('Tatort: '):
		return page_name[8:]
	return page_name

def do_tatort_template(info, params, info_attr, template, required_params):
	saved = {}
	for p in required_params:
		v = params.get(p)
		if v is not None:
			del params[p]
		if v:
			saved[p] = v
		else:
			log(info, 'Missing {} parameter {}', template, p)

	title = params.get('Titel')
	if title is not None:
		del params['Titel']
		check_title(info, template, title)
		if title != default_tatort_template_title(info.page_name):
			saved['Titel'] = title
	if params:
		log(info, 'Extraneous {} parameters|{}|', template, stringify(params))

	prev_params = getattr(info, info_attr)
	if prev_params is None:
		setattr(info, info_attr, saved)
	elif prev_params == saved:
		log(info, 'Skipping duplicate {}', template)
	else:
		prev_title = prev_params.pop('Titel', None)
		title = saved.pop('Titel', None)
		if prev_params == saved:
			log(info, 'Skipping {} with different title|{}|{}|', template, prev_title, title)
		else:
			log(info, 'Skipping different {}', template)
			log(info, '<<|{}|', stringify(prev_params))
			log(info, '>>|{}|', stringify(saved))
		if prev_title is not None:
			prev_params['Titel'] = prev_title

def do_tatort_fans(info, params):
	do_tatort_template(info, params, 'tatort_fans', 'Tatort-Fans', ('Nr', 'Url'))

def do_tatort_folge(info, params):
	url = params.get('Url', '')
	if url.startswith('/'):
		params['Url'] = url[1:]

	do_tatort_template(info, params, 'tatort_folge', 'Tatort-Folge', ('Url',))

def do_tatort_fundus(info, params):
	do_tatort_template(info, params, 'tatort_fundus', 'Tatort-Fundus', ('Jahr', 'Nr', 'Url'))

Special_Tatort_Fans_Numbers = {
	'Tatort: Angriff auf Wache 08': '1005', # instead of 1105
	'Tatort: Einmal täglich': '456', # instead of 457
}
Special_Tatort_Fundus_Numbers = {
	'Tatort: Wer jetzt allein ist': 'tatort-folge-1059', # instead of 1059
}
def check_tatort_nr(info, ep, params, template, lookup):
	n = params.get('Nr', '')
	if n == ep:
		return
	if n.startswith('0') and len(n) == 3 and n.lstrip('0') == ep:
		return
	ep = lookup.get(info.page_name, ep)
	if n != ep:
		log(info, 'Mismatched Tatort-{} episode number|{}|{}|', template, n, ep)

def get_pages():
	site = pywikibot.Site(code='de')
	return pywikibot.Page(site, 'Tatort-Folge', ns=Namespace.TEMPLATE).getReferences(
		only_template_inclusion=True)
#		only_template_inclusion=True, namespaces=(Namespace.MAIN,), total=100)

def main():
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
		skip = False
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
			skip = True
		elif Episode_Number_Pattern.match(ep):
			info.episode_number = int(ep)
		else:
			log(info, 'Invalid episode number|{}|', ep)
			skip = True

		if info.infobox_title:
			check_title(info, 'Infobox', info.infobox_title)
		else:
			log(info, 'Missing episode title')
		if not info.infobox_date:
			log(info, 'Missing episode date')
			skip = True
		if info.prev_episode is None:
			log(info, 'Missing Folgenleiste')
			skip = True

		if info.imdb is None:
			log(info, 'Missing IMDb')
		if info.tatort_fans is None:
			log(info, 'Missing Tatort-Fans')
		elif ep:
			check_tatort_nr(info, ep, info.tatort_fans, 'Fans', Special_Tatort_Fans_Numbers)
		if info.tatort_fundus and ep:
			check_tatort_nr(info, ep, info.tatort_fundus, 'Fundus', Special_Tatort_Fundus_Numbers)
		if not skip:
			info_list.append(info)

	for name, count in sorted(categories.items()):
		print('CAT', '{:5}'.format(count), name, sep='|')

	info_list.sort(key=lambda info: info.episode_number)
	last = len(info_list) - 1

	def check(info, attr, value):
		if getattr(info, attr) != value:
			log(info, 'Mismatched {}|{}|{}|', attr, getattr(info, attr), value)

	for i, info in enumerate(info_list):
		print(info.episode_number, info.infobox_date, info.episode_name,
			info.tatort_folge.get('Url', ''), sep='|')
		if i == 0:
			check(info, 'prev_episode', EnDash)
			check(info, 'prev_ep_date', EnDash)
		else:
			n = info.episode_number - 1
			orf = ORF_Episodes.get(n)
			if orf:
				if not info.prev_ep_orf:
					log(info, 'Expected " (nur ORF)" after prev_ep_date')
				prev_date, prev_name = orf[-1]
				check(info, 'prev_episode', prev_name)
				check(info, 'prev_ep_date', prev_date)
			else:
				prev = info_list[i-1]
				if prev.episode_number == n:
					check(info, 'prev_episode', prev.episode_name)
					check(info, 'prev_ep_date', prev.infobox_date)
		if i != last:
			n = info.episode_number
			orf = ORF_Episodes.get(n)
			if orf:
				if not info.next_ep_orf:
					log(info, 'Expected " (nur ORF)" after next_ep_date')
				next_date, next_name = orf[0]
				check(info, 'next_episode', next_name)
				check(info, 'next_ep_date', next_date)
			else:
				next = info_list[i+1]
				if next.episode_number == n + 1:
					check(info, 'next_episode', next.episode_name)
					check(info, 'next_ep_date', next.infobox_date)

if __name__ == '__main__':
	main()
