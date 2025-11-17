#!/bin/bash

cd /home/twfbandadmin/AssistantBot
git pull origin master
docker build -t assistantbot:latest .
docker stop assistantbot || true
docker rm assistantbot || true
docker run -d --name assistantbot --env-file .env -v ./authorized_key.json:/app/credentials/authorized_key.json --restart always  assistantbot:latest