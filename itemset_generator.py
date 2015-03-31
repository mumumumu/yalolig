# -*- coding: utf-8 -*-
import json
import os
import re
from collections import Counter
from html.parser import HTMLParser
from urllib import request

BASE_URL = 'http://champion.gg'


def open_as_firefox(url):
    req = request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return request.urlopen(req).read().decode('unicode_escape')


class ChampionGGParser(HTMLParser):
    champion_urls = set()
    patch_version = None

    def handle_starttag(self, tag, attrs):
        for attr, value in attrs:
            if attr == 'href' and re.match('/champion/\w+/\w+', value):
                self.champion_urls.add(value)

    def handle_data(self, data):
        if re.match('\d\.\d', data):
            self.patch_version = data


class ChampionItemSet():
    SKILL_MAP = str.maketrans({'1': 'Q', '2': 'W', '3': 'E', '4': 'R'})
    NAME_FORMAT = "{} ({}% | {} games)"

    CONSUMABLES = [
        {'id': '2003', 'count': 1},  # Health Potion
        {'id': '2004', 'count': 1},  # Mana Potion
        {'id': '2044', 'count': 1},  # Stealth Ward
        {'id': '2043', 'count': 1},  # Vision Ward
        {'id': '2041', 'count': 1},  # Crystalline Flask
        {'id': '2138', 'count': 1},  # Elixir of Iron
        {'id': '2137', 'count': 1},  # Elixir of Ruin
        {'id': '2139', 'count': 1},  # Elixir of Sorcery
        {'id': '2140', 'count': 1},  # Elixir of Wrath
    ]

    TRINKETS = [
        {'id': '3340', 'count': 1},  # Warding Totem
        {'id': '3341', 'count': 1},  # Sweeping Lens
        {'id': '3342', 'count': 1},  # Scrying Orb
    ]

    UPGRADED_TRINKETS = [
        {'id': '3361', 'count': 1},  # Greater Stealth Totem
        {'id': '3362', 'count': 1},  # Greater Vision Totem
        {'id': '3364', 'count': 1},  # Oracle's Lens
        {'id': '3363', 'count': 1},  # Farsight Orb
    ]

    def __init__(self, url, patch_version=None):
        self.url = BASE_URL + url
        self.patch_version = patch_version
        self.champ, self.role = url.split('/')[2:4]

    def fetch_json_data(self):
        html = open_as_firefox(self.url)
        json_string = re.findall('matchupData.championData = (.*?);\n', html)[0]

        return json.loads(re.sub('<[^<]+?>', '', json_string))

    def get_items(self, name, build_data, trinkets=False):
        item_ids = [str(item['id']) for item in build_data['items']]
        items = [{'id': item_id, 'count': count} for item_id, count in Counter(item_ids).items()]

        if trinkets:
            items += self.TRINKETS

        block = {
            'items': items,
            'type': self.NAME_FORMAT.format(name, build_data['winPercent'], build_data['games'])
        }

        return block

    def get_skills(self, build_data):
        skill_order = '-'.join(build_data['order']).translate(self.SKILL_MAP)
        formatted_skill_order = self.NAME_FORMAT.format(skill_order, build_data['winPercent'], build_data['games'])

        return formatted_skill_order

    def generate_item_set(self):
        json_data = self.fetch_json_data()
        blocks = []

        if json_data['firstItems']['mostGames']['items']:
            blocks.append(self.get_items('Most Frequent Starters', json_data['firstItems']['mostGames'], trinkets=True))

        if json_data['firstItems']['highestWinPercent']['items']:
            blocks.append(self.get_items('Highest Win Rate Starters', json_data['firstItems']['highestWinPercent'], trinkets=True))

        if json_data['items']['mostGames']['items']:
            blocks.append(self.get_items('Most Frequent Build', json_data['items']['mostGames']))

        if json_data['items']['highestWinPercent']['items']:
            blocks.append(self.get_items('Highest Win Rate Build', json_data['items']['highestWinPercent']))

        blocks.append({'items': self.CONSUMABLES, 'type': self.get_skills(json_data['skills']['mostGames'])})
        blocks.append({'items': self.UPGRADED_TRINKETS, 'type': self.get_skills(json_data['skills']['highestWinPercent'])})

        item_set = {
            'map': 'any',
            'isGlobalForChampions': False,
            'blocks': blocks,
            'associatedChampions': [],
            'title': '{} {} v{}'.format(self.champ, self.role, self.patch_version),
            'priority': False,
            'mode': 'any',
            'isGlobalForMaps': True,
            'associatedMaps': [],
            'type': 'custom',
            'softrank': 1,
            'champion': self.champ
        }

        return item_set

    def save_to_file(self):
        item_set = self.generate_item_set()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dest_dir = os.path.join(script_dir, 'Champions', self.champ, 'Recommended')

        try:
            os.makedirs(dest_dir)
        except OSError:
            pass

        filename = '{}_{}_v{}.json'.format(self.champ, self.role, self.patch_version.replace('.', ''))
        file_path = os.path.join(dest_dir, filename)
        with open(file_path, 'w') as f:
            json.dump(item_set, f)


if __name__ == "__main__":
    parser = ChampionGGParser()
    parser.feed(open_as_firefox(BASE_URL))
    for url in sorted(parser.champion_urls):
        print('Scraping {}'.format(BASE_URL + url))
        ChampionItemSet(url, patch_version=parser.patch_version).save_to_file()
