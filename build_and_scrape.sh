# Setup environment, install dependencies
sudo apt-get install bsdmainutils
virtualenv venv
. venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# Unencrypt files
git clone https://github.com/elasticdog/transcrypt.git
cd transcrypt
sudo ln -s ${PWD}/transcrypt /usr/local/bin/transcrypt
cd ..
transcrypt -c $TRANSCRYPT_CIPHER -p $TRANSCRYPT_PASSWORD -y -F
# Run daily updates
chmod u+x run_daily_updates.sh
chmod u+x run_rpscrape_script.sh
date=$(date +%Y/%m/%d -d "yesterday")
echo "Running rpscrape for date: $date"
countries=("gb" "ire")
./run_daily_updates.sh $countries $date