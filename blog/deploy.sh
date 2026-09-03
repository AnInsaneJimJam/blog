#!/bin/bash
# Write a post, run ./deploy.sh, it's live. Nothing to do on the server.
set -e
SERVER="${BLOG_SERVER:-blog-box}"          # tailscale hostname; override: BLOG_SERVER=user@host ./deploy.sh
python3 build.py
rsync -avz --delete docs/ "$SERVER:/var/www/blog/"
