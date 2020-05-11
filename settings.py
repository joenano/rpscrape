from src.utils.config import get_attribute

PROJECT_DIR = get_attribute('PROJECT_DIR')
S3_BUCKET = get_attribute('S3_BUCKET')

AWS_GLUE_DB = get_attribute('AWS_GLUE_DB')
AWS_GLUE_TABLE = get_attribute('AWS_GLUE_TABLE')

AWS_ACCESS_KEY_ID =get_attribute('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = get_attribute('AWS_SECRET_ACCESS_KEY')

SCHEMA_COLUMNS = {
     'date': 'timestamp',
     'course': 'string',
     'off': 'string',
     'name': 'string',
     'type': 'string',
     'class': 'string',
     'pattern': 'string',
     'rating_band': 'string',
     'age_band': 'string',
     'sex_rest': 'string',
     'dist': 'string',
     'dist_y': 'integer',
     'dist_m': 'integer',
     'dist_f': 'string',
     'going': 'string',
     'num': 'integer',
     'pos': 'string',
     'ran': 'integer',
     'draw': 'integer',
     'btn': 'double',
     'ovr_btn': 'double',
     'horse': 'string',
     'sp': 'string',
     'dec': 'double',
     'age': 'integer',
     'sex': 'string',
     'wgt': 'string',
     'lbs': 'integer',
     'hg': 'string',
     'time': 'double',
     'jockey': 'string',
     'trainer': 'string',
     'or': 'double',
     'rpr': 'double',
     'ts': 'double',
     'prize': 'string',
     'sire': 'string',
     'dam': 'string',
     'damsire': 'string',
     'owner': 'string',
     'comment': 'string',
     'country': 'string',
     'id': 'integer',
     'horse_cleaned': 'string',
     'jockey_clened': 'string',
     'trainer_cleaned': 'string',
 }