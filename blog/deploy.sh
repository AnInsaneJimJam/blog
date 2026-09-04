#!/bin/bash
# Write a post, run ./deploy.sh, it's live. GitHub Pages serves ../docs.
set -e
cd "$(dirname "$0")"
python3 build.py
cd ..
git add -A
git commit -m "${1:-Publish}" || echo "nothing new to commit"
git push
