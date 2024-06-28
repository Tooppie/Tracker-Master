#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd $DIR
. ~/.bash_profile
jupyter nbconvert --ExecutePreprocessor.timeout=600 --to html --execute crypto-tracker.ipynb --no-input --HTMLExporter.theme=dark
fu crypto-tracker.html
fu current_value
