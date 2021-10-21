import tomli

default_settings = {
    'auto_update': True,

    'fields': {
        'race_info': {
            'date': True,
            'region': True,
            'course_id': False,
            'course': True,
            'race_id': False,
            'off': True,
            'race_name': True,
            'type': True,
            'class': True,
            'pattern': True,
            'rating_band': True,
            'age_band': True,
            'sex_rest': True,
            'dist': True,
            'dist_f': True,
            'dist_m': True,
            'dist_y': False,
            'going': True,
            'ran': True
         },
         'runner_info': {
            'num': True,
            'pos': True,
            'draw': True,
            'ovr_btn': True,
            'btn': True,
            'horse_id': False,
            'horse': True,
            'age': True,
            'sex': True,
            'wgt': False,
            'lbs': True,
            'hg': True,
            'time': True,
            'secs': True,
            'sp': False,
            'dec': True,
            'jockey_id': False,
            'jockey': True,
            'trainer_id': False,
            'trainer': True,
            'prize': True,
            'or': True,
            'rpr': True,
            'ts': False,
            'sire_id': False,
            'sire': True,
            'dam_id': False,
            'dam': True,
            'damsire_id': False,
            'damsire': True,
            'owner_id': False,
            'owner': True,
            'silk_url': False,
            'comment': True
         }
    }
}


class Settings:

    def __init__(self):
        self.toml = self.load_toml()
        self.fields = []
        self.get_fields()
        self.field_str = ','.join([field for field in self.fields])

    def get_fields(self):
        for key in self.toml['fields']:
            for field, value in self.toml['fields'][key].items():
                if value: self.fields.append(field)

    def load_toml(self):
        try:
            return tomli.load(open('../settings.toml', 'r'))
        except tomli.TOMLDecodeError:
            print('Failed to load settings.toml')
            choice = input('Do you want to continue with default settings? (Y/N):  ').lower().strip()
            if choice != 'y':
                return None
            return default_settings
