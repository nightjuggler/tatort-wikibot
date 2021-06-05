import re
import tatort_wiki_lib as TW

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

	def set_sortkey(self, suffix, ep):
		if suffix == '':
			self.sortkey = ep
			return True
		if suffix == ', ' + str(ep + 1):
			self.sortkey = ep
			self.double_episode = True
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

def main():
	TW.Infobox_Stats.init()

	info_list = TW.process_pages(TatortInfo, get_urls)

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
