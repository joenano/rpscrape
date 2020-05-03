#!/bin/bash
echo "setting project_dir to ./scripts"
countries=("$2@")
cd ./scripts
for country in "${countries[@]}"; do
	echo "Running scraper. Date: $1, Country: $country"
	echo "-d $1 $2" | python3 rpscrape.py
done