#!/bin/bash
watchmedo auto-restart \
    --debounce-interval 2 \
    --directory . \
    --pattern .reload-trigger \
    --no-restart-on-command-exit \
    python3 -- bot.py
