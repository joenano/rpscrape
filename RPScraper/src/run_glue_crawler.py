import awswrangler as wr
import boto3
import sys

mode = sys.argv[1]
print(f'Mode (overwrite/append table): {mode}')

from RPScraper.settings import S3_BUCKET, AWS_GLUE_DB, AWS_GLUE_TABLE,\
    AWS_SECRET_ACCESS_KEY, AWS_ACCESS_KEY_ID

session = boto3.session.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)
# Run crawler
print("Running crawler")
res = wr.s3.store_parquet_metadata(
    path=f"s3://{S3_BUCKET}/datasets/",
    database=AWS_GLUE_DB,
    table=AWS_GLUE_TABLE,
    dataset=True,
    use_threads=True,
    boto3_session=session,
    mode=mode
)
# Delete the crawled files
print("Deleting files stored in /datasets/")
wr.s3.delete_objects(f"s3://{S3_BUCKET}/datasets/", use_threads=True, boto3_session=session)
