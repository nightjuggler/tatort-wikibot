import re
import tatort_wiki_lib as TW

log = TW.log

TW.Series = 'Polizeiruf 110'
TW.Series_Prefix = 'Polizeiruf 110: '
TW.Alternate_Titles = {
	'Polizeiruf 110: In Erinnerung an …': '"In Erinnerung an …"',
}

class TatortInfo(object):
	def __init__(self, page_name):
		self.page_name = page_name
		self.episode_name, self.page_suffix = TW.get_episode_name(page_name)
		self.prev_episode = None
		self.next_episode = None
		self.imdb = None
		self.episode_number = None
		self.infobox_title = None
		self.infobox_date = None
		self.double_episode = False

	def get_sortkey(self, suffix, ep):
		if suffix == '':
			return ep
		if suffix == ' & ' + str(ep + 1):
			self.double_episode = True
			return ep
		return None

TW.Infobox_Series_Params.extend((
	('Serie',         True,  'Polizeiruf 110'),
	('Serienlogo',    False, ''),
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

def main():
	info_list = TW.process_pages(TatortInfo, get_urls)

	next_ep = 1
	prev = None

	for info in info_list:
		ep = info.sortkey
		if ep != next_ep:
			log(info, 'Unexpected episode number|{}|{}', ep, next_ep)
		elif prev:
			TW.check_attrs(info, 'prev', prev)
			TW.check_attrs(prev, 'next', info)
		else:
			TW.check_attr(info, 'prev_episode', '')
			TW.check_attr(info, 'prev_ep_date', '')

		if info.double_episode:
			print(ep, info.infobox_date, info.episode_name + ' (1)', info.url, sep='|')
			print(ep+1, info.part2_date, info.episode_name + ' (2)', info.url, sep='|')
			next_ep = ep + 2
		else:
			print(info.episode_number, info.infobox_date, info.episode_name, info.url, sep='|')
			next_ep = ep + 1
		prev = info

	if prev:
		TW.check_attr(prev, 'next_episode', '')
		TW.check_attr(prev, 'next_ep_date', '')

if __name__ == '__main__':
	main()
