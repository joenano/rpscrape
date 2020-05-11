#!/bin/bash
countries=("$1")
for country in "${countries[@]}"; do
	./scripts/run_rpscrape_script.sh "$2" "$country" || echo "Completed"
done
