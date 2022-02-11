import os.path
import tomli

class Settings:

    def __init__(self):
        self.toml = self.load_toml()
        if self.toml is None: return
        
        self.fields = self.get_fields()
        self.csv_header = ','.join([field for field in self.fields])

    def get_fields(self):
        fields = []
        for key in self.toml['fields']:
            for field, value in self.toml['fields'][key].items():
                if value: fields.append(field)
        return fields
    
    def load_toml(self):
        path_default_settings = '../settings/default_settings.toml'
        path_user_settings = '../settings/user_settings.toml'
        
        settings_file = self.open_file(path_user_settings)
        if settings_file is None:
            print(f'{path_user_settings} does not exist, using {path_default_settings}')

            settings_file = self.open_file(path_default_settings)
            if settings_file is None:
                raise Exception(f'{path_default_settings} does not exist')
                return None
            
        toml = self.parse_toml(settings_file)
        return None if toml is None else toml
            
    def open_file(self, file_path):
        if os.path.isfile(file_path):
            return open(file_path, 'rb')
        return None
    
    def parse_toml(self, settings_file):
        try:
            return tomli.load(settings_file)
        except tomli.TOMLDecodeError:
            print('TomlParseError: ', settings_file.name)
            return None
