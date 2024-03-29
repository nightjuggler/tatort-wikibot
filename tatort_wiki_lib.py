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

	'Jänner':    1, # Tatort: Die Faust (Parameter 'Premiere' in Vorlage 'Infobox Episode')
}
Month_Days = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
Day_Pattern = '([1-9][0-9]?)\\.'
Month_Pattern = '(?: |&nbsp;)([A-Z][a-zä]{2,8}\\.?)'
Year_Pattern = '([12][0-9]{3})'
Date_Pattern = re.compile(f'{Day_Pattern}{Month_Pattern} +{Year_Pattern}')
Before_Date_Pattern = re.compile(f'^{Day_Pattern}(?:{Month_Pattern})? +und +$')
Special_Dates = {}

def parse_date_before(info, param, extra, date, month, year):
	if param == 'VG-DATUM':
		attr = 'prev_ep_date2'
	elif param == 'NF-DATUM':
		attr = 'next_ep_date2'
	elif param == 'Sender':
		return extra.startswith('[[') and extra.endswith(']] (Teil 1)<br />')
	else:
		return False

	m = Before_Date_Pattern.match(extra)
	if not m:
		return False

	day, month2 = m.groups()
	day = int(day)
	if month2:
		month = Months.get(month2, 0)

	if month == 0 or day > Month_Days[month - 1]:
		log(info, 'Invalid date before date|{}={}|', param, date)
		return True

	setattr(info, attr, f'{year}-{month:02}-{day:02}')
	return True

def parse_date_after(info, param, extra):
	if param == 'Sender':
		return extra == ' ebd. (Teil 2)'
	return False

def parse_date(info, param, date):
	date = date.replace('\n', '\\n')
	m = Date_Pattern.search(date)
	if m is None:
		special = Special_Dates.get((info.page_name, param))
		if special:
			if date == special[0]:
				return special[1]
		elif date in ('', EnDash) and param in ('VG-DATUM', 'NF-DATUM'):
			return ''
		log(info, 'Cannot parse date|{}={}|', param, date)
		return ''

	day, month, year = m.groups()
	day, month, year = int(day), Months.get(month, 0), int(year)

	if month == 0 or day > Month_Days[month - 1]:
		log(info, 'Invalid date|{}={}|', param, date)
		return ''

	extra = date[:m.start()]
	if extra and not parse_date_before(info, param, extra, date, month, year):
		log(info, 'Extra text before date|{}={}|', param, date)
	extra = date[m.end():]
	if extra and not parse_date_after(info, param, extra):
		log(info, 'Extra text after date|{}={}|', param, date)

	return f'{year}-{month:02}-{day:02}'

class Infobox_Stats(object):
	Spec = (
		'Serie                            |+ ',
		'Serienlogo                       |+ ',
		'Reihe                            |+ ',
		'Bild                             |  ',
		'Titel                            |  ',
		'Originaltitel                    |+ ',
		'Produktionsland                  |+g',
		'Produktionsunternehmen           |+ ',
		'Originalsprache                  |+g',
		'Länge                            |+g',
		'Staffel                          |- ',
		'Episode                          |+ ',
		'Episode_gesamt                   |- ',
		'Episodenliste                    |+ ',
		'Premiere                         |+ ',
		'Premiere_DE                      |- ',
		'Sender                           |+g',
		'Sender_DE                        |- ',
		'FSK                              |  ',
		'JMK                              |  ',
		'Regie                            |+ ',
		'Drehbuch                         |+ ',
		'Produzent                        |+ ',
		'Musik                            |+ ',
		'Kamera                           |+ ',
		'Schnitt                          |+ ',
		'Besetzung                        |+ ',
		'Synchronisation                  |- ',
		'Chronologie                      |+ ',
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
			*names, flags = map(str.strip, names.split('|'))

			groups[tuple(names)] = group = self.Group(names, flags)
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

Ref_Pattern = re.compile('<ref(?:(?:>[^<>]+</ref>)|(?: +name *= *"[- 0-9A-Z_a-z]+" */>))')

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
			value = Ref_Pattern.sub('', value).replace('\n', '\\n')
			groups[value] = groups.get(value, 0) + 1
		if group.seen:
			log(info, 'Should specify only one Infobox parameter {}', name)
		else:
			group.seen = True

def check_infobox_common(info, params):
	for p in (
		'Besetzung',
		'Drehbuch',
		'Kamera',
		'Länge',
		'Originalsprache',
		'Produktionsland',
		'Regie',
		'Schnitt',
		'Sender',
	):
		if p not in params:
			log(info, 'Missing Infobox parameter {}', p)

Infobox_Series_Params = [
	('Reihe', True, 'ja'),
]
def check_infobox_normal(info, params, series_params=Infobox_Series_Params):
	for p, required, x in series_params:
		v = params.get(p)
		if v is None:
			if required:
				log(info, 'Missing Infobox parameter {}', p)
		elif v != x if v else required:
			log(info, 'Unexpected value for Infobox parameter {}|{}', p, v)

def check_infobox_special(info, params):
	series_params = (
		('Reihe',      True, 'ja'),
		('Serie',      True, 'Tatort (Fernsehreihe)'),
		('Episode',    True, "142 der Reihe ''[[Polizeiruf 110]]''<br /> und 235"),
	)
	check_infobox_normal(info, params, series_params)

	for p in ('Serienlogo', 'Episodenliste'):
		if p in params:
			log(info, 'Unexpected Infobox parameter {}', p)

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
			return name[:i-1], name[i+1:-1]
	return name, None

def check_title(info, template, title, part=None):
	title = title.replace('&nbsp;', ' ')
	if info.double_episode and part:
		for suffix in (' ({})', ' (Teil {})', ' Teil {}'):
			suffix = suffix.format(part)
			if title.endswith(suffix):
				title = title.removesuffix(suffix)
				break
		else:
			log(info, 'Mismatched {} title|{}|', template, title)
			return
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
	info.prev_ep_date = parse_date(info, 'VG-DATUM', params.pop('VG-DATUM', ''))
	info.next_ep_date = parse_date(info, 'NF-DATUM', params.pop('NF-DATUM', ''))
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

	for p in ('Originaltitel', 'Titel'):
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
				log(info, 'Use Originaltitel instead of {}', p)
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

	for p in ('Premiere', 'Premiere_DE'):
		v = params.get(p)
		if not v:
			continue
		v = parse_date(info, p, v)
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
				log(info, 'Use Premiere instead of {}', p)
		elif date == v:
			log(info, 'Duplicate Infobox date|{}|{}', date_param, p)
		else:
			log(info, '{} and {} are different', p, date_param)

	return set_infobox_date(info, date)

def set_episode_number(info, ep):
	if info.episode_number is not None:
		log(info, 'Episode number already specified')
		return
	info.episode_number = ep
	if m := Episode_Number_Pattern.match(ep):
		i = m.end()
		info.sortkey = info.get_sortkey(ep[i:], int(ep[:i]))
	else:
		info.sortkey = None

def do_infobox_episode(info, params):
	get_infobox_date(info, params)
	get_infobox_title(info, params)

	if info.infobox_title == 'Unter Brüdern':
		check_infobox_special(info, params)
		set_episode_number(info, '235' if Series == 'Tatort' else '142')
	else:
		check_infobox_normal(info, params)
		set_episode_number(info, params.get('Episode', ''))

	if info.double_episode:
		info.part2_date = parse_date(info, 'Sender', params.get('Sender', ''))

	check_infobox_common(info, params)
	update_infobox_stats(info, params)

def check_attr(info, attr, value):
	if getattr(info, attr, '') != value:
		log(info, 'Mismatched {}|{}|{}|', attr, getattr(info, attr, ''), value)

def check_attrs(info, attr, prev):
	check_attr(info, attr + '_episode', prev.episode_name)
	if prev.double_episode:
		check_attr(info, attr + '_ep_date', prev.part2_date)
		check_attr(info, attr + '_ep_date2', prev.infobox_date)
	else:
		check_attr(info, attr + '_ep_date', prev.infobox_date)
		check_attr(info, attr + '_ep_date2', '')
	name = prev.page_name
	link = getattr(info, attr + '_ep_page') or Series_Prefix + getattr(info, attr + '_episode')
	if link != name and link != name.replace(' ', '_'):
		log(info, 'Mismatched {}_ep_page|{}|{}|', attr, link, name)

def process_pages(info_class, process_page, *other_actions):
	categories = {}
	templates = {}
	Infobox_Stats.init()
	info_list = []

	navbar = 'Folgenleiste {}-Folgen'.format(Series.replace(' ', '-'))
	template_actions = {
		navbar: do_folgenleiste,
		'IMDb': do_imdb,
		'Infobox Episode': do_infobox_episode,
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
		if not info.sortkey:
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

	Infobox_Stats.write(series + '-infobox-stats.txt')

	info_list.sort(key=lambda info: info.sortkey)
	return info_list
