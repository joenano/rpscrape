#!/bin/bash
countries=("$1")
for country in "${countries[@]}"; do
	./run_rpscrape_script.sh "$2" "$country"
done
