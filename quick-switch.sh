#!/bin/bash
STATIONS=$(awk '/name:/ {gsub(/name: /,""); print}' ~/.config/radio-scheduler/config.yaml)
CHOICE=$(echo "$STATIONS" | rofi -dmenu -i -p "Radio")
[ -z "$CHOICE" ] && exit
URL=$(grep -A1 "name: \"$CHOICE\"" ~/.config/radio-scheduler/config.yaml | grep url | awk '{print $2}' | tr -d '"')
mpc clear
mpc add "$URL"
mpc play
notify-send "RadioScheduler" "→ $CHOICE"
