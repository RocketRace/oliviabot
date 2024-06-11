#!/bin/bash
trap 'kill 0' SIGINT
# run in background
cargo watch --quiet --exec check --shell 'touch .watch-trigger' &
cargo watch --no-vcs-ignores --watch .watch-trigger --postpone --exec run &
wait
