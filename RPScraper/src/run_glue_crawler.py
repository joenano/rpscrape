import awswrangler as wr
import boto3
import datetime as dt
import sys

mode = 'overwrite'  #sys.argv[1]
print(f"Mode (overwrite/append): {mode}")

from RPScraper.settings import S3_BUCKET, AWS_GLUE_DB, AWS_GLUE_TABLE, \
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

session = boto3.session.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)
# Run crawler
print("Running crawler")
t1 = dt.datetime.now()
res = wr.s3.store_parquet_metadata(
    path=f"s3://{S3_BUCKET}/datasets/",
    database=AWS_GLUE_DB,
    table=AWS_GLUE_TABLE,
    dataset=True,
    use_threads=True,
    mode=mode,
    boto3_session=session,
)
print(f'Crawler took {(dt.datetime.now() - t1).total_seconds()}')
