`oliviabot` is a discord bot for joy.

Bootstrapping steps for future reference:
```sh
tmux new -s oliviabot
curl -sSL https://install.python-poetry.org | python3 -
curl -fsSL https://pyenv.run | bash
# add to .bashrc
# export PATH="$HOME/.pyenv/bin:$PATH"
# eval "$(pyenv init --path)"
# restart tmux if needed
pyenv install 3.13 --verbose
pyenv local 3.13
poetry install --only main
python3 run.py prod
```