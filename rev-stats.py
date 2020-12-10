import pywikibot
import re
import sys

def log(message, *args, **kwargs):
	print(message.format(*args, **kwargs), file=sys.stderr)

def err(*args, **kwargs):
	log(*args, **kwargs)
	sys.exit()

def date2str(d):
	return '{}-{:02}-{:02} {:02}:{:02}:{:02}'.format(d.year, d.month, d.day, d.hour, d.minute, d.second)

class User(object):
	name2user = {}
	sortkey = {
		'articles': lambda u: (u.num_articles, u.num_authored, u.num_contribs, u.name),
		'authored': lambda u: (u.num_authored, u.num_contribs, u.num_articles, u.name),
		'contribs': lambda u: (u.num_contribs, u.num_authored, u.num_articles, u.name),
	}

	def __init__(self, name, anon):
		self.name = name
		self.anon = anon
		self.num_articles = 0
		self.num_authored = 0
		self.num_contribs = 0

	def check_oldest_newest(self, date, oldest_attr, newest_attr):
		oldest = getattr(self, oldest_attr, None)
		if oldest is None or date < oldest:
			setattr(self, oldest_attr, date)

		newest = getattr(self, newest_attr, None)
		if newest is None or newest < date:
			setattr(self, newest_attr, date)

	def inc_articles(self, date):
		self.num_articles += 1
		self.check_oldest_newest(date, 'date_oldest_articles', 'date_newest_articles')

	def inc_authored(self, date):
		self.num_authored += 1
		self.check_oldest_newest(date, 'date_oldest_authored', 'date_newest_authored')

	def inc_contribs(self, date):
		self.num_contribs += 1
		self.check_oldest_newest(date, 'date_oldest_contribs', 'date_newest_contribs')

	@classmethod
	def get(self, name, anon):
		user = self.name2user.get(name)
		if not user:
			self.name2user[name] = user = self(name, anon)
		elif user.anon != anon:
			log('User "{}" was previously {}anonymous', name, 'not ' if anon else '')
		return user

	@classmethod
	def print_stats(self, attr):
		sortkey = self.sortkey.get(attr)
		if not sortkey:
			log('No sortkey for attr "{}"', attr)
			return
		attr_authored = attr == 'authored'
		oldest_attr = 'date_oldest_' + attr
		newest_attr = 'date_newest_' + attr
		total_oldest = None
		total_newest = None
		print('+---------------------------------------+')
		print('|', ('Most ' + attr).center(37), '|')
		print('+------+----------+----------+----------+---------------------+---------------------+')
		print('| Rank | Articles | Authored | Contribs |       Oldest        |       Newest        |')
		print('+------+----------+----------+----------+---------------------+---------------------+')
		n = 0
		total_authored = 0
		total_contribs = 0
		for user in sorted(self.name2user.values(), key=sortkey, reverse=True):
			if user.num_authored == 0:
				if attr_authored: break
			else:
				total_authored += user.num_authored
			total_contribs += user.num_contribs
			n += 1
			user_oldest = getattr(user, oldest_attr)
			user_newest = getattr(user, newest_attr)
			if total_oldest is None or user_oldest < total_oldest:
				total_oldest = user_oldest
			if total_newest is None or total_newest < user_newest:
				total_newest = user_newest
			if n > 20:
				continue
			print('|{:5} |{:9,} |{:9,} |{:9,} | {} | {} | {}'.format(n,
				user.num_articles,
				user.num_authored,
				user.num_contribs,
				date2str(user_oldest),
				date2str(user_newest),
				user.name))
		print('+-----------------+----------+----------+---------------------+---------------------+')
		print('| {:9,} users |{:9,} |{:9,} | {} | {} |'.format(n,
			total_authored,
			total_contribs,
			date2str(total_oldest),
			date2str(total_newest),
			))
		print('+-----------------+----------+----------+---------------------+---------------------+')

class Year(object):
	name2year = {}

	def __init__(self):
		self.num_articles = 0
		self.num_authored = 0
		self.num_contribs = 0

	@classmethod
	def get(self, name):
		year = self.name2year.get(name)
		if not year:
			self.name2year[name] = year = self()
		return year

	@classmethod
	def print_stats(self):
		print('+--------------------------------+')
		print('|             Years              |')
		print('+----------+----------+----------+')
		print('| Articles | Authored | Contribs |')
		print('+----------+----------+----------+')
		total_authored = 0
		total_contribs = 0
		for name, year in sorted(self.name2year.items(), reverse=True):
			total_authored += year.num_authored
			total_contribs += year.num_contribs
			print('|{:9,} |{:9,} |{:9,} | {}'.format(
				year.num_articles,
				year.num_authored,
				year.num_contribs, name))
		print('+----------+----------+----------+')
		print('|   Total: |{:9,} |{:9,} |'.format(total_authored, total_contribs))
		print('+----------+----------+----------+')

Namespace = pywikibot.site.Namespace

def get_pages(sitecode, template, total=None):
	site = pywikibot.Site(code=sitecode)
	return pywikibot.Page(site, template, ns=Namespace.TEMPLATE).getReferences(
		only_template_inclusion=True, namespaces=(Namespace.MAIN,), total=total)

def parse_total(value):
	value = int(value)
	if value < 0:
		raise ValueError('must be >= 0')
	return value

def parse_args(args):
	param_pattern = re.compile('^[a-z]+=')
	short_selector_pattern = re.compile('^[a-z][-0-9a-z]*$')
	selector_pattern = re.compile('^([a-z]{2}):([A-Z][- 0-9A-Za-z]*)$')

	valid_params = {
		'total': parse_total,
	}
	valid_selectors = {
		'tatort': ('de', 'Folgenleiste Tatort-Folgen'),
		'polizeiruf110': ('de', 'Folgenleiste Polizeiruf-110-Folgen'),
	}

	params = {}
	selector = None

	for arg in args:
		m = param_pattern.match(arg)
		if m:
			i = m.end()
			param = arg[:i-1]
			value = arg[i:]
			parse = valid_params.get(param)
			if not parse:
				err('Invalid command-line parameter "{}"', param)
			try:
				params[param] = parse(value)
			except ValueError:
				err('Invalid value for command-line parameter "{}"', param)
			continue

		if selector:
			err('Please specify only one page selector.')

		m = short_selector_pattern.match(arg)
		if m:
			selector = arg
			continue

		m = selector_pattern.match(arg)
		if m:
			selector = m.groups()
			continue

		err('Invalid command-line argument "{}"', arg)

	if not selector:
		selector = 'tatort'
	if isinstance(selector, str):
		selector = valid_selectors.get(selector)
		if not selector:
			err('Invalid page selector!')

	return (selector, params)

def main(args):
	args, kwargs = parse_args(args)
	n = 0
	for page in get_pages(*args, **kwargs):
		n += 1
		log('{:,} | {}', n, page.title())
		revisions = page.revisions(reverse=True, starttime=None, endtime=None)
		rev = next(revisions)
		date = rev.timestamp
		user = User.get(rev.user, rev.anon)
		user.inc_articles(date)
		user.inc_authored(date)
		user.inc_contribs(date)
		users = {user}
		year = Year.get(date.year)
		year.num_articles += 1
		year.num_authored += 1
		year.num_contribs += 1
		years = {year}
		for rev in revisions:
			date = rev.timestamp
			user = User.get(rev.user, rev.anon)
			user.inc_contribs(date)
			if user not in users:
				user.inc_articles(date)
				users.add(user)
			year = Year.get(date.year)
			year.num_contribs += 1
			if year not in years:
				year.num_articles += 1
				years.add(year)

	Year.print_stats()
	User.print_stats('contribs')
	User.print_stats('authored')
	User.print_stats('articles')

if __name__ == '__main__':
	main(sys.argv[1:])
