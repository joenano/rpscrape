from re import search

from collections.abc import Callable
from lxml.html import HtmlElement


# class Pedigree:
#     def __init__(self, pedigrees: list[HtmlElement]):
#         self.pedigrees: list[HtmlElement] = pedigrees
#         self.dams: list[str] = []
#         self.damsires: list[str] = []
#         self.sires: list[str] = []
#         self.id_dams: list[str] = []
#         self.id_damsires: list[str] = []
#         self.id_sires: list[str] = []
#
#         self.pedigree_info()
#
#     def clean_name(self, name: str) -> str:
#         return name.replace('.', ' ').replace('  ', ' ').replace(',', '').replace("'", '').strip()
#
#     def get_dam(self, info_dam):
#         dam = self.clean_name(info_dam.text.strip().strip('()'))
#         dam_nat = info_dam.find('span').text
#
#         if dam_nat is not None:
#             region_dam = dam_nat.strip()
#         else:
#             region_dam = 'GB'
#
#         return f'{dam} {region_dam}'
#
#     def get_damsire(self, info_damsire):
#         damsire = self.clean_name(info_damsire.text.strip('()'))
#
#         if damsire == 'Damsire Unregistered':
#             damsire = ''
#
#         return damsire.strip('()')
#
#     def get_sire(self, info_sire):
#         sire = info_sire.text.strip()
#
#         if '(' in sire:
#             region_sire = search(r'\((.*)\)', sire).groups()[0]
#         else:
#             region_sire = 'GB'
#
#         sire = self.clean_name(sire.split('(')[0])
#
#         return f'{sire} ({region_sire})'
#
#     def pedigree_info(self):
#         for pedigree in self.pedigrees:
#             ped_info = pedigree.findall('a')
#
#             if '-' in pedigree.text_content():
#                 if len(ped_info) > 0:
#                     self.sires.append(self.get_sire(ped_info[0]))
#                     self.id_sires.append(ped_info[0].attrib['href'].split('/')[3])
#                 else:
#                     self.sires.append('')
#                     self.id_sires.append('')
#
#                 if len(ped_info) > 1:
#                     self.dams.append(self.get_dam(ped_info[1]))
#                     self.id_dams.append(ped_info[1].attrib['href'].split('/')[3])
#                 else:
#                     self.dams.append('')
#                     self.id_dams.append('')
#
#                 if len(ped_info) > 2:
#                     self.damsires.append(self.get_damsire(ped_info[2]))
#                     self.id_damsires.append(ped_info[2].attrib['href'].split('/')[3])
#                 else:
#                     self.damsires.append('')
#                     self.id_damsires.append('')
#             else:
#                 self.sires.append('')
#                 self.id_sires.append('')
#
#                 if len(ped_info) > 0:
#                     self.dams.append(self.get_dam(ped_info[0]))
#                     self.id_dams.append(ped_info[0].attrib['href'].split('/')[3])
#                 else:
#                     self.dams.append('')
#                     self.id_dams.append('')
#
#                 if len(ped_info) > 1:
#                     self.damsires.append(self.get_damsire(ped_info[1]))
#                     self.id_damsires.append(ped_info[1].attrib['href'].split('/')[3])
#                 else:
#                     self.damsires.append('')
#                     self.id_damsires.append('')


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

    def clean_name(self, name: str) -> str:
        return name.replace('.', ' ').replace('  ', ' ').replace(',', '').replace("'", '').strip()

    def get_dam(self, info_dam: HtmlElement) -> str:
        text: str = info_dam.text or ''
        dam: str = self.clean_name(text.strip().strip('()'))

        span: HtmlElement | None = info_dam.find('span')
        dam_nat: str | None = span.text if span is not None else None
        region_dam: str = dam_nat.strip() if dam_nat else 'GB'

        return f'{dam} {region_dam}'

    def get_damsire(self, info_damsire: HtmlElement) -> str:
        text: str = info_damsire.text or ''
        damsire: str = self.clean_name(text.strip('()'))

        if damsire == 'Damsire Unregistered':
            return ''

        return damsire.strip('()')

    def get_sire(self, info_sire: HtmlElement) -> str:
        text: str = info_sire.text or ''
        sire: str = text.strip()

        if '(' in sire:
            match = search(r'\((.*)\)', sire)
            region_sire: str = match.groups()[0] if match else 'GB'
        else:
            region_sire = 'GB'

        sire = self.clean_name(sire.split('(')[0])

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

            # sire
            self._append_entry(
                self.sires,
                self.id_sires,
                ped_info,
                0 if has_sire else -1,
                self.get_sire,
            )

            # dam
            dam_index = 1 if has_sire else 0
            self._append_entry(self.dams, self.id_dams, ped_info, dam_index, self.get_dam)

            # damsire
            damsire_index = dam_index + 1
            self._append_entry(
                self.damsires, self.id_damsires, ped_info, damsire_index, self.get_damsire
            )
