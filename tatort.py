import re
import sys

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

def read_html():
	expected_prefix1 = '<select name="filterBoxTitle" '
	expected_prefix2 = '<option value="/">Bitte '
	expected_prefix3 = '</select>'
	episode_pattern = re.compile('^<option value="([0-9a-z]+(?:-[0-9a-z]+)*-?[0-9]{3})">'
		' *(.+) \\(([0-9]{2}\\.[0-9]{2}\\.[0-9]{4})\\)</option>$')

	html_episodes = []
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
				('2017-01-22', 'Tatort: Schock'),
			):
				log('Skipping "{}" ({}) {}', title, date, url)
				continue
			if (date, title) == ('2014-12-12', 'Der Maulwurf'):
				date = '2014-12-21'
			elif (date, title) == ('1980-02-17', 'Der gelbe Unterrock'):
				date = '1980-02-10'
			elif (date, title) == ('1979-06-14', 'Ein Schuss zuviel'):
				date = '1979-06-04'

			html_episodes.append((date, title, url))

	html_episodes.append(('2017-06-18',
		'Borowski und das Fest des Nordens',
		'borowski-und-das-fest-des-nordens-104'))

	html_episodes.sort()
	return html_episodes

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

	wiki_episodes = {}
	with InputFile(TATORT_WIKI_EPISODES) as f:
		for line in f:
			ep, date, title, url = line.split('|')
			unexpected_chars = title_pattern.sub('', title)
			if unexpected_chars:
				log('Unexpected characters [{}] in "{}"',
					', '.join(['U+{:04X}'.format(ord(ch)) for ch in unexpected_chars]), title)
			title = title_map.get(title, title)
			wiki_episodes[int(ep)] = (date, title, url[:-1])

	return wiki_episodes

def html2txt():
	html_episodes = read_html()
	for ep, info in enumerate(html_episodes, start=1):
		print(ep, *info, sep='|')

def fetch():
	import subprocess

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
		'fetch': fetch,
		'html2txt': html2txt,
	}
	command = commands.get(args.pop(0) if args else 'html2txt')
	if not command:
		err('Please specify a valid command.')
	command()

if __name__ == '__main__':
	main(sys.argv[1:])
