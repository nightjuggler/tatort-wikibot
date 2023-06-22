import re
import tatort_wiki_lib as TW

log = TW.log

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

TW.Special_Dates = {
	('Tatort: Schock', 'Premiere'): ('22. [[Jänner]] 2017', '2017-01-22'),
	('Zabou (Film)', 'Premiere'): ('1990-07-22', '1990-07-22'),
}
TW.Alternate_Infobox_Dates = {
	'Tatort: Exklusiv!': ('1969-10-26', '1971-07-11'),
	'Tatort: Mord hinterm Deich': ('1996-12-25', '1997-06-08'),
	'Tatort: Time-Out': ('2001-09-23', '2002-12-22'),
	'Tatort: Seenot': ('2008-01-13', '2008-03-24'),
	'Tatort: Der Polizistinnenmörder': ('2010-01-03', '2010-01-17'),
	'Tatort: Die Amme': ('2021-03-14', '2021-03-28'),
}
TW.Alternate_Titles = {
	'Tatort: Acht, neun – aus': 'Acht, neun – aus!',
	'Tatort: Aus der Traum (2006)': 'Aus der Traum …',
	'Tatort: Die schlafende Schöne': 'Die Schlafende Schöne',
	'Tatort: Laura mein Engel': 'Laura, mein Engel',
	'Tatort: Liebe mich!': 'Liebe mich',
	'Tatort: Murot und das Prinzip Hoffnung': 'Das Prinzip Hoffnung',
	'Tatort: Romeo und Julia': 'Romeo & Julia',
	'Tatort: Stirb und werde': 'Stirb und Werde',
	'Tatort: Tote Taube in der Beethovenstraße': 'Kressin: Tote Taube in der Beethovenstraße',
	'Tatort: Wat Recht is, mutt Recht blieben': 'Wat Recht is, mutt Recht bliewen',
	'Tatort: … es wird Trauer sein und Schmerz': '... es wird Trauer sein und Schmerz',
}

def parse_date_after(info, param, extra):
	if extra == ' (nur ORF)':
		if param == 'VG-DATUM':
			info.prev_orf = True
			return True
		if param == 'NF-DATUM':
			info.next_orf = True
			return True
	elif param == 'Sender':
		return extra == ' ebd. (Teil 2)'
	return False

TW.parse_date_after = parse_date_after

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
		self.tatort_fans = None
		self.tatort_folge = None
		self.double_episode = False
		self.orf = False
		self.prev_orf = False
		self.next_orf = False

	def get_sortkey(self, suffix, ep):
		if suffix == '':
			return ep, 0
		if suffix == 'a':
			self.orf = True
			return ep, 1
		if suffix == 'b':
			self.orf = True
			return ep, 2
		suffix = suffix.split()
		if len(suffix) == 2 and suffix[1] == str(ep + 1) and suffix[0] in ('&', 'und'):
			self.episode_number = str(ep)
			self.double_episode = True
			return ep, 0
		return None

TW.Infobox_Series_Params.extend((
	('Serie',         True,  'Tatort (Fernsehreihe)'),
	('Serienlogo',    False, 'Tatort Logo mini.svg'),
	('Episodenliste', True,  'Liste der Tatort-Folgen'),
))

def do_infobox_film(info, params):
	if not TW.get_infobox_title(info, params):
		return
	if info.infobox_title == 'Tschiller: Off Duty':
		TW.set_infobox_date(info, '2018-07-08')
		TW.set_episode_number(info, '1062')

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

Tatort_Fans_URL_Map = {}
Tatort_Folge_URL_Map = {}

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
def check_tatort_nr(info, params, template, lookup):
	n = params.pop('Nr', None)
	if not n:
		log(info, 'Missing Tatort-{} episode number', template)
		return None
	ep = lookup.get(info.page_name, info.episode_number)
	if n == ep:
		return 1
	if len(n) == 3 and n[0] == '0' and n.lstrip('0') == ep:
		return 1
	if info.double_episode and n == str(int(ep) + 1):
		return 2
	log(info, 'Mismatched Tatort-{} episode number|{}|{}|', template, n, ep)
	return None

def check_tatort_fans(info):
	expected_url = Tatort_Fans_URL_Map.get(info.episode_number, title2url(info.episode_name))
	url_suffix = ('', '-teil-1', '-teil-2')

	for params in info.tatort_fans:
		part = check_tatort_nr(info, params, 'Fans', Special_Tatort_Fans_Numbers)
		if part is None: continue

		url = params.pop('Url', '').lower().rstrip('/')
		if not url:
			log(info, 'Missing Tatort-Fans URL')
		else:
			_url = expected_url
			if info.double_episode:
				_url += url_suffix[part]
			if url != _url:
				mismatched_url(info, url, _url, 'Fans')

		title = params.pop('Titel', None)
		if title is not None:
			TW.check_title(info, 'Tatort-Fans', title, part)
		elif info.page_suffix:
			log(info, 'Should specify Tatort-Fans title')

		if params:
			log(info, 'Extraneous Tatort-Fans parameters|{}|', TW.stringify(params))

def check_double_episode_url(info, prev_url, url, expected_url):
	if url[:-3] == expected_url + 'folge-1-':
		part = 1
	elif url[:-3] == expected_url + 'folge-2-':
		part = 2
	else:
		mismatched_url(info, url[:-3], expected_url + 'folge-[12]-', 'Folge')
		return None
	prev = prev_url[part-1]
	if prev is None:
		prev_url[part-1] = url
	elif url != prev:
		log(info, 'Tatort-Folge with different URL|{}|{}|', url, prev)
	return part

def check_tatort_folge(info):
	expected_url = Tatort_Folge_URL_Map.get(info.episode_number, title2url(info.episode_name) + '-')
	prev_url = [None]*2 if info.double_episode else None

	for params in info.tatort_folge:
		part = None
		url = params.pop('Url', None)
		if not url:
			log(info, 'Missing Tatort-Folge URL')
		elif not (len(url) > 3
			and 49 <= ord(url[-3]) <= 50 # [12]
			and 48 <= ord(url[-2]) <= 57 # [0-9]
			and 48 <= ord(url[-1]) <= 57 # [0-9]
		):
			log(info, 'Invalid Tatort-Folge URL suffix|{}|', url)
		else:
			if url[0] == '/':
				url = url[1:]
			if info.double_episode:
				part = check_double_episode_url(info, prev_url, url, expected_url)
			elif url[:-3] != expected_url:
				mismatched_url(info, url[:-3], expected_url, 'Folge')
			elif not prev_url:
				prev_url = url
			elif url != prev_url:
				log(info, 'Tatort-Folge with different URL|{}|{}|', url, prev_url)

		title = params.pop('Titel', None)
		if title is not None:
			TW.check_title(info, 'Tatort-Folge', title, part)
		elif info.page_suffix:
			log(info, 'Should specify Tatort-Folge title')

		if params:
			log(info, 'Extraneous Tatort-Folge parameters|{}|', TW.stringify(params))

	info.tatort_folge = prev_url

def ep2str(ep):
	n, x = ep
	ep = str(n)
	return ep + chr(96 + x) if x else ep

def check_info(info, page):
	if info.tatort_fans:
		check_tatort_fans(info)
	elif not info.orf:
		log(info, 'Missing Tatort-Fans')
	if info.tatort_folge:
		check_tatort_folge(info)
	elif not info.orf:
		log(info, 'Missing Tatort-Folge')

def main():
	load_url_map('tatort-fans-url-map.txt', Tatort_Fans_URL_Map)
	load_url_map('tatort-folge-url-map.txt', Tatort_Folge_URL_Map)

	info_list = TW.process_pages(TatortInfo, check_info,
		('Infobox Film', do_infobox_film),
		('Tatort-Fans', do_tatort_fans),
		('Tatort-Folge', do_tatort_folge))

	next_ep = (1, 0)
	prev = None

	for info in info_list:
		ep = info.sortkey
		if ep != next_ep:
			log(info, 'Unexpected episode number|{}|{}', ep2str(ep), ep2str(next_ep))
		elif prev:
			if prev.orf != info.prev_orf:
				log(info, '{}xpected " (nur ORF)" after prev_ep_date', 'E' if prev.orf else 'Une')
			if info.orf != prev.next_orf:
				log(prev, '{}xpected " (nur ORF)" after next_ep_date', 'E' if info.orf else 'Une')
			TW.check_attrs(info, 'prev', prev)
			TW.check_attrs(prev, 'next', info)
		else:
			TW.check_attr(info, 'prev_episode', TW.EnDash)
			TW.check_attr(info, 'prev_ep_date', '')

		if info.double_episode:
			name = info.episode_name
			if urls := info.tatort_folge:
				if urls[0]: print(ep[0], info.infobox_date, name + ' (1)', urls[0], sep='|')
				if urls[1]: print(ep[0]+1, info.part2_date, name + ' (2)', urls[1], sep='|')
			ep = (ep[0] + 1, 0)
		elif info.tatort_folge:
			print(info.episode_number, info.infobox_date, info.episode_name, info.tatort_folge, sep='|')

		next_ep = (ep[0], ep[1] + 1) if info.next_orf else (ep[0] + 1, 0)
		prev = info

	if prev:
		TW.check_attr(prev, 'next_episode', TW.EnDash)
		TW.check_attr(prev, 'next_ep_date', '')

if __name__ == '__main__':
	main()
