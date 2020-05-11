import awswrangler as wr

from RPScraper.settings import S3_BUCKET, AWS_GLUE_DB, AWS_GLUE_TABLE

# Run crawler
print("Running crawler")
res = wr.s3.store_parquet_metadata(
    path=f"s3://{S3_BUCKET}/datasets/",
    database=AWS_GLUE_DB,
    table=AWS_GLUE_TABLE,
    dataset=True
)