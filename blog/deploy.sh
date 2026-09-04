#!/bin/bash
# Write a post, run ./deploy.sh, it's live.
set -e
cd "$(dirname "$0")"
SERVER="${BLOG_SERVER:-anand@debian-server}"   # override: BLOG_SERVER=user@host ./deploy.sh
python3 build.py
rsync -avz --delete ../docs/ "$SERVER:/var/www/blog/"
