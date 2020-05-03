#!/bin/bash
echo "setting project_dir to ./scripts"
cd ./scripts
echo "Running scraper. Date: $1, Country: $country"
echo "-d $1 $2" | python3 rpscrape.py