from lxml.html import HtmlElement

from utils.cleaning import normalize_name
from utils.lxml_funcs import find


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


class Odds:
    def __init__(self, doc: HtmlElement):
        self.horses = {}

        rows = doc.xpath("//div[@data-test-selector='RC-oddsRunnerContent__runnerRow']")

        for row in rows:
            name = normalize_name(find(row, 'a', 'RC-oddsRunnerContent__runnerName'))
            prices = row.xpath(".//div[@class='RC-oddsRunnerContent__data']")

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
