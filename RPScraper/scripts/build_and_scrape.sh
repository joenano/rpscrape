# Setup environment, install dependencies
sudo apt-get install bsdmainutils
virtualenv venv
. venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# Run daily updates
chmod u+x ./scripts/run_daily_updates.sh
chmod u+x ./scripts/run_rpscrape_script.sh
date=$(date +%Y/%m/%d -d "yesterday")
echo "Running rpscrape for date: $date"
countries=("gb" "ire")
./scripts/run_daily_updates.sh $countries $date