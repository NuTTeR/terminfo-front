#!/bin/bash

cd "$(dirname "$0")" # Смена директори на текущую
while true; do
  python3 main.py >> /tmp/terminfo.log 2>&1 # Запуск приложения
  sleep 1
done