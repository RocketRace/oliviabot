`oliviabot` is a discord bot for joy.

Bootstrapping steps for future reference:
```sh
tmux new -s oliviabot
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.11
curl -sSL https://install.python-poetry.org | python3 -
poetry env use 3.11
$(poetry env activate)
poetry install --only main
python3 run.py prod
```