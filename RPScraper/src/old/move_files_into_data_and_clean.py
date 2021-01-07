import awswrangler as wr
import boto3

from RPScraper.src.utils.s3_tools import list_files, move_file
from RPScraper.settings import S3_BUCKET

session = boto3.session.Session()

files = list_files(bucket=S3_BUCKET, prefix='')
files2 = [f.get('Key') for f in files if 'data' not in f.get('Key')]
for file in files2:
    print(file)
    move_file(source=f"{S3_BUCKET}/{file}",
              destination=f"data/{file}", bucket=S3_BUCKET)

# Delete any left over files
files = wr.s3.list_objects(path=f"s3://{S3_BUCKET}/")
files2 = [f for f in files if 'data' not in f]
wr.s3.delete_objects(files2, use_threads=True)
