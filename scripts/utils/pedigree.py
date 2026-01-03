from re import search

from collections.abc import Callable
from lxml.html import HtmlElement

from utils.cleaning import clean_string


class Pedigree:
    def __init__(self, pedigrees: list[HtmlElement]) -> None:
        self.pedigrees: list[HtmlElement] = pedigrees
        self.dams: list[str] = []
        self.damsires: list[str] = []
        self.sires: list[str] = []
        self.id_dams: list[str] = []
        self.id_damsires: list[str] = []
        self.id_sires: list[str] = []

        self.pedigree_info()

    def get_dam(self, info_dam: HtmlElement) -> str:
        text: str = info_dam.text or ''
        dam: str = clean_string(text.strip().strip('()'))

        span: HtmlElement | None = info_dam.find('span')
        dam_nat: str | None = span.text if span is not None else None
        region_dam: str = dam_nat.strip() if dam_nat else '(GB)'

        return f'{dam} {region_dam}'

    def get_damsire(self, info_damsire: HtmlElement) -> str:
        text: str = info_damsire.text or ''
        text = text.strip().strip('()')
        damsire: str = clean_string(text)

        if damsire == 'Damsire Unregistered':
            return ''

        return damsire

    def get_sire(self, info_sire: HtmlElement) -> str:
        text: str = info_sire.text or ''
        sire: str = text.strip()

        if '(' in sire:
            match = search(r'\((.*)\)', sire)
            region_sire: str = match.groups()[0] if match else 'GB'
        else:
            region_sire = 'GB'

        sire = clean_string(sire.split('(')[0])

        return f'{sire} ({region_sire})'

    def _append_entry(
        self,
        collection: list[str],
        id_collection: list[str],
        ped_info: list[HtmlElement],
        index: int,
        transform: Callable[[HtmlElement], str],
    ) -> None:
        if len(ped_info) > index:
            element = ped_info[index]
            collection.append(transform(element))
            id_collection.append(element.attrib.get('href', '').split('/')[3])
        else:
            collection.append('')
            id_collection.append('')

    def pedigree_info(self) -> None:
        for pedigree in self.pedigrees:
            ped_info: list[HtmlElement] = pedigree.findall('a')
            has_sire: bool = '-' in pedigree.text_content()

            self._append_entry(
                self.sires,
                self.id_sires,
                ped_info,
                0 if has_sire else -1,
                self.get_sire,
            )

            dam_index = 1 if has_sire else 0
            self._append_entry(self.dams, self.id_dams, ped_info, dam_index, self.get_dam)

            damsire_index = dam_index + 1
            self._append_entry(
                self.damsires, self.id_damsires, ped_info, damsire_index, self.get_damsire
            )
