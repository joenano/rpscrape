# Setup environment, install dependencies
sudo apt-get install bsdmainutils
virtualenv venv
. venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# Run daily updates
cd RPScraper || exit
chmod u+x ./scripts/run_daily_updates.sh
chmod u+x ./scripts/run_rpscrape_script.sh

if [ -z "$1" ]
  then
    echo "No argument supplied, running for yesterdays date"
    date=$(date +%Y/%m/%d -d "yesterday")
  else
    echo "No argument supplied, running for {$1}"
    date="$1"
fi

echo "Running rpscrape for date: $date"
countries=("gb" "ire")
./scripts/run_daily_updates.sh $countries $date