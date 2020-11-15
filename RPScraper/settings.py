import boto3

from RPScraper.src.utils.config import get_attribute

boto3_session = boto3.session.Session()

PROJECT_DIR = get_attribute('PROJECT_DIR')
S3_BUCKET = get_attribute('S3_BUCKET')

AWS_GLUE_DB = get_attribute('AWS_GLUE_DB')
AWS_GLUE_TABLE = get_attribute('AWS_GLUE_TABLE')

AWS_ACCESS_KEY_ID = get_attribute('AWS_ACCESS_KEY_ID')
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
     'dist_y': 'int',
     'dist_m': 'int',
     'dist_f': 'string',
     'going': 'string',
     'num': 'int',
     'pos': 'string',
     'ran': 'int',
     'draw': 'int',
     'btn': 'double',
     'ovr_btn': 'double',
     'horse': 'string',
     'sp': 'string',
     'dec': 'double',
     'age': 'int',
     'sex': 'string',
     'wgt': 'string',
     'lbs': 'int',
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
     'id': 'int',
     'horse_cleaned': 'string',
     'jockey_cleaned': 'string',
     'trainer_cleaned': 'string',
     'year': 'int'
 }
