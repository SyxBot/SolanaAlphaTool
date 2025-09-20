#!/usr/bin/env bash
set -e

# repo-local logs dir
mkdir -p logs

# start services
nohup python apps/pumpfun-bot/run_bot.py > logs/pumpfun.log 2>&1 &
nohup node apps/eliza-ingest/server.js > logs/eliza.log 2>&1 &

echo "started. logs -> ./logs"
