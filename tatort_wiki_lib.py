import pywikibot
import re
import sys

def log(info, format_spec, *args):
	print('LOG', info.page_name, format_spec.format(*args), sep='|')

def stringify(params):
	return '|'.join(['='.join(p) for p in sorted(params.items())])

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
Date_Pattern = re.compile('^(?:\\{\\{0\\}\\})?([1-9][0-9]?)\\.(?: |&nbsp;)([A-Z][a-zä]+\\.?) +([12][0-9]{3})')
Special_Dates = {}

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

class Infobox_Stats(object):
	Spec = (
		'Franchise               |',
#		'Art                     |',
		'Serie                   | SERIE  |  ',
		'Serie_Link              | SLINK  |  ',
		'Reihe                   | REIHE  |+ ',
		'Titel                   | DT     |- ',
		'Originaltitel           | OT     |+ ',
#		'Transkription           | TRANS  |  ',
		'Untertitel              | UT     |  ',
		'Bild                    | BILD   |  ',
		'Produktionsland         | PL     |+g',
		'Produktionsunternehmen  | PROU   |  ',
		'Originalsprache         | OS     |+g',
		'Länge                   | LEN    |  ',
		'Staffel                 | ST     |- ',
		'Episode                 | EP     |+ ',
		'Episode_gesamt          | EPG    |- ',
		'Erstausstrahlung        | EAS    |+ ',
#		'Erstveröffentlichung    | EVÖ    |- ',
		'Sender                  | SEN    |+g',
		'Erstausstrahlung_DE     | EASDE  |- ',
#		'Erstveröffentlichung_DE | EVÖDE  |- ',
		'Sender_DE               | SENDE  |- ',
		'Altersfreigabe          | AF|FSK |  ',
		'BMUKK                   | JMK    |  ',
		'Regie                   | REG    |+ ',
		'Drehbuch                | DRB    |+ ',
		'Produzent               | PRO    |  ',
		'Musik                   | MUSIK  |  ',
		'Kamera                  | KAMERA |+ ',
		'Schnitt                 | SCHNITT|+ ',
		'Besetzung               | DS     |+ ',
		'Gastauftritt            | GAST   |+ ',
		'Synchronisation         | SYN    |- ',
		'Episodenliste           | EPL    |+ ',
		'Chronologie             | CHR    |+ ',
	)

	class Param(object):
		Lookup = {}
		def __init__(self, group):
			self.num_used = 0
			self.num_empty = 0
			self.group = group
			group.params.append(self)

	class Group(object):
		Lookup = {}
		def __init__(self, names, flags):
			self.num_used = 0
			self.num_empty = 0
			self.must_use = 0
			self.groups = None
			self.params = []

			for flag in flags:
				if   flag == '-': self.must_use = -1
				elif flag == '+': self.must_use = 1
				elif flag == 'g': self.groups = {}
				else:
					print('Unknown flag "{}" for "{}"'.format(flag, ', '.join(names)),
						file=sys.stderr)

		@classmethod
		def clear_seen(self):
			for group in self.Lookup.values():
				group.seen = False

	@classmethod
	def init(self):
		params = self.Param.Lookup
		groups = self.Group.Lookup

		for names in self.Spec:
			names = names.split('|')
			flags = names[-1].strip()
			names = tuple([name.strip() for name in names[:-1]])

			groups[names] = group = self.Group(names, flags)
			for name in names:
				params[name] = self.Param(group)

	@classmethod
	def write_params(self, f, attr):
		print('------+', attr, 'Infobox Parameters ----', file=f)
		attr = 'num_' + attr.lower()
		for names, group in sorted(self.Group.Lookup.items()):
			num = getattr(group, attr)
			if num == 0: continue
			print(' {:4} |'.format(num), ', '.join(['{} ({})'.format(name, getattr(param, attr))
				for name, param in zip(names, group.params)]), file=f)

	@classmethod
	def write_groups(self, f):
		for names, group in sorted(self.Group.Lookup.items()):
			groups = group.groups
			if groups is None: continue
			print('------+', ', '.join(names), '----', file=f)
			for value, num in sorted(groups.items()):
				print(' {:4} |'.format(num), value, file=f)

	@classmethod
	def write(self, filename):
		with open(filename, 'w') as f:
			self.write_params(f, 'Used')
			self.write_params(f, 'Empty')
			self.write_groups(f)

def update_infobox_stats(info, params):
	Infobox_Stats.Group.clear_seen()
	param_lookup = Infobox_Stats.Param.Lookup

	for name, value in params.items():
		param = param_lookup.get(name)
		if not param:
			log(info, 'Should remove Infobox parameter {}', name)
			continue
		group = param.group
		if value:
			param.num_used += 1
			group.num_used += 1
			if group.must_use < 0:
				log(info, 'Infobox parameter {} should be empty', name)
		else:
			param.num_empty += 1
			group.num_empty += 1
			if group.must_use > 0:
				log(info, 'Infobox parameter {} should not be empty', name)
		groups = group.groups
		if groups is not None:
			groups[value] = groups.get(value, 0) + 1
		if group.seen:
			log(info, 'Should specify only one Infobox parameter {}', name)
		else:
			group.seen = True

def check_infobox_common(info, params):
	for p1, p2 in (
		('DRB',     'Drehbuch'),
		('DS',      'Besetzung'),
		('KAMERA',  'Kamera'),
		('OS',      'Originalsprache'),
		('PL',      'Produktionsland'),
		('REG',     'Regie'),
		('SCHNITT', 'Schnitt'),
		('SEN',     'Sender'),
	):
		if not (p1 in params or p2 in params):
			log(info, 'Missing Infobox parameter {}', p2)

def check_infobox_nonseries(info, params):
	param_lookup = Infobox_Stats.Param.Lookup
	deleted = [(name, param_lookup.pop(name)) for name in (
		'DT',    'Titel',
		'EP',    'Episode',
		'EPL',   'Episodenliste',
		'OT',    'Originaltitel',
		'REIHE', 'Reihe',
		'SLINK', 'Serie_Link',
	)]
	update_infobox_stats(info, params)
	param_lookup.update(deleted)

Infobox_Series_Params = [
	('Reihe', True, 'ja'),
]
def check_infobox_series(info, params):
	for p, required, x in Infobox_Series_Params:
		v = params.get(p)
		if v is None:
			if required:
				log(info, 'Missing Infobox parameter {}', p)
		elif v != x if v else required:
			log(info, 'Unexpected value for Infobox parameter {}|{}', p, v)

Series = 'Tatort'
Series_Prefix = Series + ': '
Alternate_Infobox_Dates = {}
Alternate_Titles = {}
Episode_Number_Pattern = re.compile('^[1-9][0-9]*')
PageName_Suffix_Pattern = re.compile('^ \\((?:[12][0-9]{3}|Film)\\)$')

def get_episode_name(name):
	if name.startswith(Series_Prefix):
		name = name[len(Series_Prefix):]
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
	if title == Series_Prefix + info.episode_name:
		return
	log(info, 'Mismatched {} title|{}|', template, title)

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
		for i, c in enumerate(v):
			if c == '<' or c == '[':
				log(info, 'Markup after title|{}|{}', p, v)
				v = v[:i].rstrip()
				break
		if not title:
			title = v
			title_param = p
			if p[0] != 'O':
				log(info, 'Use OT/Originaltitel instead of {}', p)
		elif title == v:
			log(info, 'Duplicate Infobox title|{}|{}', title_param, p)
		else:
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

def set_episode_number(info, ep):
	if info.episode_number is None:
		info.episode_number = ep
		return True
	log(info, 'Previous Infobox already specified episode number')
	return False

def do_infobox_episode(info, params):
	series = params.get('Serie')
	if series != Series:
		if series:
			log(info, 'Skipping Infobox for another series|{}|', series)
			return

		check_infobox_nonseries(info, params)
		check_infobox_common(info, params)
		get_infobox_date(info, params)
		return

	set_episode_number(info, params.get('Episode', ''))
	check_infobox_series(info, params)

	if not params.get('Franchise'):
		check_infobox_common(info, params)
		get_infobox_title(info, params)
		get_infobox_date(info, params)

	update_infobox_stats(info, params)

def do_medienbox(info, params):
	set_infobox_title(info, params.get('Titel'))

def check_episode_number(info, ep):
	m = Episode_Number_Pattern.match(ep)
	if m:
		i = m.end()
		return info.set_sortkey(ep[i:], int(ep[:i]))
	return False

def process_pages(info_class, process_page, *other_actions):
	categories = {}
	templates = {}
	info_list = []

	navbar = 'Folgenleiste {}-Folgen'.format(Series.replace(' ', '-'))
	template_actions = {
		navbar: do_folgenleiste,
		'IMDb': do_imdb,
		'Infobox Episode': do_infobox_episode,
		'Medienbox': do_medienbox,
	}
	template_actions.update(other_actions)

	Namespace = pywikibot.site.Namespace
	main_ns = Namespace.MAIN

	site = pywikibot.Site(code='de')
	pages = pywikibot.Page(site, navbar, ns=Namespace.TEMPLATE).getReferences(
		only_template_inclusion=True, namespaces=(main_ns,))

	for page in pages:
		info = info_class(page.title())

		ns = page.namespace()
		if ns.id != main_ns:
			log(info, 'Not in the main namespace|{}|', ns.canonical_name)
			continue

		for cat in page.categories():
			name = cat.title()
			categories[name] = categories.get(name, 0) + 1

		for name, params in page.raw_extracted_templates:
			if name.startswith(('SORTIERUNG:', 'DEFAULTSORT:')):
				continue
			action = template_actions.get(name)
			if action:
				action(info, params)
			templates[name] = templates.get(name, 0) + 1

		ep = info.episode_number
		if ep is None:
			log(info, 'Missing {} Infobox', Series)
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

		process_page(info, page)
		info_list.append(info)

	series = Series.replace(' ', '').lower()

	with open(series + '-categories.txt', 'w') as f:
		for name, count in sorted(categories.items()):
			print('{:5}'.format(count), name, sep=' | ', file=f)

	with open(series + '-templates.txt', 'w') as f:
		for name, count in sorted(templates.items()):
			print('{:5}'.format(count), name, sep=' | ', file=f)

	info_list.sort(key=lambda info: info.sortkey)
	return info_list
