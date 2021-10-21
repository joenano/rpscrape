from re import search


class Pedigree:
    
    def __init__(self, pedigrees):
        self.pedigrees = pedigrees
        self.dams = []
        self.damsires = []
        self.sires = []
        self.id_dams = []
        self.id_damsires = []
        self.id_sires = []
        
        self.pedigree_info()
        
    def clean_name(self, name):
        return name.replace('.', ' ').replace('  ', ' ').replace(',', '')\
            .replace("'", '').strip()
        
    def get_dam(self, info_dam):
        dam = self.clean_name(info_dam.text.strip().strip('()'))
        dam_nat = info_dam.find('span').text
        
        if dam_nat is not None:
            region_dam = dam_nat.strip()
        else:
            region_dam = 'GB'
            
        return f'{dam} {region_dam}'
    
    def get_damsire(self, info_damsire):
        damsire = self.clean_name(info_damsire.text.strip('()'))
        
        if damsire == 'Damsire Unregistered':
            damsire = ''
        
        return damsire.strip('()')
    
    def get_sire(self, info_sire):
        sire = info_sire.text.strip()
                    
        if '(' in sire:
            region_sire = search('\((.*)\)', sire).groups()[0]
        else:
            region_sire = 'GB'
            
        sire = self.clean_name(sire.split('(')[0])
        
        return f'{sire} ({region_sire})'
                
    def pedigree_info(self):
        for pedigree in self.pedigrees:
            ped_info = pedigree.findall('a')

            if '-' in pedigree.text_content():
                if len(ped_info) > 0:
                    self.sires.append(self.get_sire(ped_info[0]))
                    self.id_sires.append(ped_info[0].attrib['href'].split('/')[3])
                else:
                    self.sires.append('')
                    self.id_sires.append('')

                if len(ped_info) > 1:
                    self.dams.append(self.get_dam(ped_info[1]))
                    self.id_dams.append(ped_info[1].attrib['href'].split('/')[3])
                else:
                    self.dams.append('')
                    self.id_dams.append('')

                if len(ped_info) > 2:
                    self.damsires.append(self.get_damsire(ped_info[2]))
                    self.id_damsires.append(ped_info[2].attrib['href'].split('/')[3])
                else:
                    self.damsires.append('')
                    self.id_damsires.append('')
            else:
                self.sires.append('')
                self.id_sires.append('')

                if len(ped_info) > 0:
                    self.dams.append(self.get_dam(ped_info[0]))
                    self.id_dams.append(ped_info[0].attrib['href'].split('/')[3])
                else:
                    self.dams.append('')
                    self.id_dams.append('')

                if len(ped_info) > 1:
                    self.damsires.append(self.get_damsire(ped_info[1]))
                    self.id_damsires.append(ped_info[1].attrib['href'].split('/')[3])
                else:
                    self.damsires.append('')
                    self.id_damsires.append('')
