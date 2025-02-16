import sys

from collections import defaultdict

from utils.lxml_funcs import find, xpath


BOOKIES = {
    'WH_OXI': 'william_hill',
    'LADB': 'ladbrokes',
    'BET365': 'bet365',
    'CORAL': 'coral',
    'PPWR': 'paddy_power',
    'BETFAIR': 'betfair_sb',
    'SURREY': 'skybet',
    'BOLEYSPORTS': 'boylesports',
}


def clean_name(name):
    if name:
        return name.strip().replace("'", '').lower().title()
    else:
        return ''


class Odds:
    def __init__(self, doc):
        self.horses = {}

        rows = xpath(doc, 'div', 'RC-oddsRunnerContent__runnerRow')

        for row in rows:
            name = clean_name(find(row, 'a', 'RC-oddsRunnerContent__runnerName'))
            prices = xpath(row, 'div', 'RC-oddsRunnerContent__data', 'class')

            odds = {}

            for price in prices:
                bookie = price.attrib['data-diffusion-bookmaker']
                link = price.find('a')

                if bookie not in BOOKIES:
                    continue
                bookie = BOOKIES[bookie]

                print(link.attrib['data-diffusion-fractional'])
                odds[bookie] = price

            self.horses[name] = dict(odds)
