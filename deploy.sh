#!/bin/bash

cd $HOME/cherang-bot
git pull

pip3 install --user -r requirements.txt

pm2 restart cherang

echo "✨ Cherang Bot 업데이트 완료!"

