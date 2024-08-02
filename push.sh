set -e
changes=$($py scripts/trigger_updates.py)
~/.local/bin/poetry env use 3.12
py=$(~/.local/bin/poetry env info --executable)
if [ -z $changes ]; then
    echo "No actions needed"
elif [ $changes == bot ]; then
echo "Restarting bot"
tmux send -t oliviabot C-c
sleep 2
tmux send -t oliviabot python3 Space run.py Space prod Enter
elif [ $changes == dependencies ]; then
echo "Updating dependencies and restarting bot"
~/.local/bin/poetry install --only main
tmux send -t oliviabot C-c
sleep 2
tmux send -t oliviabot python3 Space run.py Space prod Enter
elif [ $changes == cogs ]; then
echo "Scheduled cog reload"
fi
