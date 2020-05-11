# Set up virutal environment
virtualenv venv
. venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd RPScraper
# Add environment variables
export PROJECT_DIR=/home/circleci/project/RPScraper
export S3_BUCKET=rpscrape
export AWS_GLUE_DB=finish-time-predict
export AWS_GLUE_TABLE=rpscrape
export AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
export PYTHONPATH=/home/circleci/project
python RPScraper/src/run_glue_crawler.py