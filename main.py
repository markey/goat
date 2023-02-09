from discord.ext import commands
from plugins import gpt, sd, img2prompt
import json
import os

import util.history

with open("config.json") as f:
    config = json.load(f)


class Config:
    def __init__(self, filename="config.json"):
        with open("config.json") as f:
            self.config = json.load(f)

    def __getattr__(self, key):
        return self.config[key]


BOT_NAME = "goat"

config = Config()

bot = commands.Bot(command_prefix="!")


@bot.event
async def on_ready():
    print("Ready!")


history = util.history.MessageHistory(config.history_length)
for cog in [gpt, sd, img2prompt]:
    bot.add_cog(cog.Bot(bot, config, history))

bot.run(os.environ["DISCORD_TOKEN"])
