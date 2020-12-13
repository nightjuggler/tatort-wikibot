import os.path
import random
import re
import subprocess
import sys
import time

TATORT_HTML = 'tatort.html'
TATORT_HTML_URL = 'https://www.daserste.de/unterhaltung/krimi/tatort/sendung/index.html'
TATORT_TITLE_MAP = 'tatort-title-map.txt'
TATORT_WIKI_EPISODES = 'tatort-wiki-episodes.txt'

def log(message, *args, **kwargs):
	print(message.format(*args, **kwargs), file=sys.stderr)

def err(*args, **kwargs):
	log(*args, **kwargs)
	sys.exit()

class InputFile(object):
	def __init__(self, fileName):
		self.lineNumber = 0
		self.fileObject = open(fileName)

	def close(self):
		self.fileObject.close()

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.close()
		return False

	def __iter__(self):
		return self

	def __next__(self):
		line = self.fileObject.__next__()
		self.lineNumber += 1
		return line

	next = __next__

REPLACE_WITH_DASH = re.compile('[^0-9a-z]+')
TRANSLATION_TABLE = str.maketrans({
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
	url = title.lower().translate(TRANSLATION_TABLE)
	url = REPLACE_WITH_DASH.sub('-', url)

	if url[0] == '-':
		url = url[1:]
	if url[-1] == '-':
		url = url[:-1]

	return url

def fans_html_url(start=None, end=None):
	if not start:
		start = 1970
	if not end:
		end = time.gmtime().tm_year + 1
	urls = [
		'tatort-1970-1979',
		'archiv-1980-1989',
		'tatort-1990-1999',
		'tatort-2000-2009',
		'archiv-2010-2019',
		'archiv-2020-202x',
	]
	for year in range(start, end + 1):
		url = urls[year // 10 - 197]
		year_str = str(year)
		yield (
			'tatort-fans/' + year_str + '.html',
			'https://tatort-fans.de/category/' + url + '/' + year_str + '/',
		)

def fans_read_html():
	episode_number_errors = {
		'45-der-schwarze-skorpion': 456,
		'456-einmal-taeglich': 457,
		'674-nachtgefluester': 675,
		'1005-angriff-auf-wache-08': 1105,
	}
	episode_number_pattern = re.compile('^(?:[1-9][0-9]{1,3}|0[0-9]{2})-')
	episodes = []

	for html, url in fans_html_url():
		if not os.path.exists(html):
			continue
		with InputFile(html) as f:
			for line in f:
				if 'entry-title' not in line:
					continue
				line = line.split('\"')[3]
				if line[:30] != 'https://tatort-fans.de/tatort-':
					log('{}, line {}: Unexpected URL prefix: {}', html, f.lineNumber, line)
					continue
				if line[-1] != '/':
					log('{}, line {}: Unexpected URL suffix: {}', html, f.lineNumber, line)
					continue
				line = line[30:-1]
				folge = False
				if line[:6] == 'folge-':
					folge = True
					line = line[6:]
				m = episode_number_pattern.match(line)
				if not m:
					log('{}, line {}: Episode number pattern doesn\'t match: {}',
						html, f.lineNumber, line)
					continue
				i = m.end()
				ep = episode_number_errors.get(line, int(line[:i-1]))
				episodes.append((ep,  line[i:]))
				if folge != (ep > 171) and ep not in (34, 55, 84, 129):
					log('URL for episode {} has "folge-" prefix', line)

	episodes.sort()
	return episodes

def fans_urlmap():
	wiki_titles = {}
	with InputFile(TATORT_WIKI_EPISODES) as f:
		for line in f:
			ep, date, title, url = line.split('|')
			wiki_titles[int(ep)] = title

	for ep, url in fans_read_html():
		wiki_title = wiki_titles.get(ep)
		if wiki_title is None:
			continue
		if url != title2url(wiki_title):
			print(ep, url, sep='|')

def fans_html2txt():
	for ep, url in fans_read_html():
		print(ep, url, sep='|')

def parse_fans_year(arg, arg_name, min_year, max_year):
	try:
		year = int(arg)
		if min_year <= year <= max_year:
			return year
	except ValueError:
		pass

	err('The {} year must be a number between {} and {}.', arg_name, min_year, max_year)

def parse_fans_fetch_args(args):
	if not args:
		return (None, None)

	end = time.gmtime().tm_year + 1

	start = parse_fans_year(args.pop(0), 'start', 1970, end)
	if not args:
		return (start, start)

	end = parse_fans_year(args.pop(0), 'end', start, end)
	if not args:
		return (start, end)

	err('Too many command-line arguments!')

def fans_fetch(args):
	start, end = parse_fans_fetch_args(args)

	rc = 1
	for html, url in fans_html_url(start, end):
		if rc == 0:
			sleep_time = int(random.random() * 5 + 5.5)
			print('Sleeping for', sleep_time, 'seconds', file=sys.stderr)
			time.sleep(sleep_time)

		command = ['/usr/bin/curl', '-o', html, url]
		print(*command, file=sys.stderr)
		rc = subprocess.call(command)
		if rc != 0:
			err('Exit code', rc)

	fans_html2txt()

def read_html():
	expected_prefix1 = '<select name="filterBoxTitle" '
	expected_prefix2 = '<option value="/">Bitte '
	expected_prefix3 = '</select>'
	episode_pattern = re.compile('^<option value="([0-9a-z]+(?:-[0-9a-z]+)*-?[0-9]{3})">'
		' *(.+) \\(([0-9]{2}\\.[0-9]{2}\\.[0-9]{4})\\)</option>$')

	episodes = []
	with InputFile(TATORT_HTML) as f:
		for line in f:
			if line.startswith(expected_prefix1):
				break
		else:
			err('Expected "{}"', expected_prefix1)

		line = f.next()
		if not line.startswith(expected_prefix2):
			err('Expected "{}"', expected_prefix2)

		for line in f:
			m = episode_pattern.match(line)
			if not m:
				if line.startswith(expected_prefix3):
					break
				err('Expected episode pattern or "{}" on line {}:\n{}', expected_prefix3,
					f.lineNumber, line)

			url, title, date = m.groups()
			date = '-'.join(reversed(date.split('.')))

			if (date, title) in (
				('2016-11-13', 'Sonntagsmörder'), # Sonntagsmörder – Ermittlung über 1000 Tatorte
			):
				log('Skipping "{}" ({}) {}', title, date, url)
				continue
			if (date, title) == ('2014-12-12', 'Der Maulwurf'):
				date = '2014-12-21'
			elif (date, title) == ('1980-02-17', 'Der gelbe Unterrock'):
				date = '1980-02-10'
			elif (date, title) == ('1979-06-14', 'Ein Schuss zuviel'):
				date = '1979-06-04'

			episodes.append((date, title, url))

	episodes.append(('2017-06-18',
		'Borowski und das Fest des Nordens',
		'borowski-und-das-fest-des-nordens-104'))

	episodes.sort()
	return episodes

def read_wiki():
	title_map = {}
	with InputFile(TATORT_TITLE_MAP) as f:
		for line in f:
			title_map[line[:-1]] = f.next()[:-1]

	special_chars = (
		'\u2013' # en dash
		'\u2019' # apostrophe (right single quotation mark)
		'\u2026' # ellipsis
	)
	title_pattern = re.compile('[- !,.0-9:?A-Za-zÄÜäöüßâàéô' + special_chars + ']+')

	episodes = {}
	with InputFile(TATORT_WIKI_EPISODES) as f:
		for line in f:
			ep, date, title, url = line.split('|')
			unexpected_chars = title_pattern.sub('', title)
			if unexpected_chars:
				log('Unexpected characters [{}] in "{}"',
					', '.join(['U+{:04X}'.format(ord(ch)) for ch in unexpected_chars]), title)
			title = title_map.get(title, title)
			episodes[int(ep)] = (date, title, url[:-1])

	return episodes

def urlmap():
	wiki_titles = {}
	with InputFile(TATORT_WIKI_EPISODES) as f:
		for line in f:
			ep, date, title, url = line.split('|')
			wiki_titles[int(ep)] = title

	for ep, (date, title, url) in enumerate(read_html(), start=1):
		wiki_title = wiki_titles.get(ep)
		if wiki_title is None:
			continue
		wiki_url = title2url(wiki_title) + '-'
		if not (len(url) > 3 and url[-3] in '12' and url[-2] in '0123456789' and url[-1] in '02468'):
			log('Unexpected URL suffix: "{}"', url)
		url = url[:-3]
		if url != wiki_url:
			print(ep, url, sep='|')

def html2txt():
	for ep, info in enumerate(read_html(), start=1):
		print(ep, *info, sep='|')

def fetch():
	command = ['/usr/bin/curl', '-o', TATORT_HTML, TATORT_HTML_URL]

	rc = subprocess.call(command)
	if rc != 0:
		err('Exit code', rc)

	html2txt()

def diff():
	wiki_episodes = read_wiki()
	html_episodes = read_html()

	for ep, info in enumerate(html_episodes, start=1):
		wiki_info = wiki_episodes.get(ep)
		if not wiki_info:
			print('ADD', ep, *info, sep='|')
			continue
		if wiki_info == info:
			continue
		for name, value, wiki_value in zip(('DATE', 'TITLE', 'URL'), info, wiki_info):
			if value != wiki_value:
				print('MOD', ep, name, wiki_value, value, sep='|')

def main(args):
	commands = {
		'diff': diff,
		'fans_fetch': fans_fetch,
		'fans_html2txt': fans_html2txt,
		'fans_urlmap': fans_urlmap,
		'fetch': fetch,
		'html2txt': html2txt,
		'urlmap': urlmap,
	}
	command = commands.get(args.pop(0) if args else 'html2txt')
	if not command:
		err('Please specify a valid command.')
	if command.__code__.co_argcount == 1:
		command(args)
	else:
		command()

if __name__ == '__main__':
	main(sys.argv[1:])
