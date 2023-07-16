# goat

simply the world's greatest discord bot.

## future plans


## setup

poetry is used for dependency management. you can install it with pipx:

pipx install poetry

then, install the dependencies:

poetry install

then to run:

poetry run main.py

you will need to register an application on discord:
https://discordpy.readthedocs.io/en/stable/discord.html

you will need an openai key.  you can request your own which will come with plenty of quota for development. i may also be able to add you to my project.

You will need a qdrant api key.

## contributing

please run pre-commit install to install standard pre-commit hooks.

## cost management
- the open ai queries are billed on a per-token basis.  token count per english request can be estimated by dividing the length by four.  the davinci engine is $0.02/1k tokens.
