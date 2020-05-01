#!/bin/bash
echo "running command $1"
cd scripts
python3 rpscrape.py <<< $1