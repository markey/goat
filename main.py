from discord.ext import commands
from plugins import gpt, sd, img2prompt, openjourney
import json
import os

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

for cog in [gpt, sd, img2prompt, openjourney]:
    bot.add_cog(cog.Bot(bot, config))

bot.run(os.environ["DISCORD_TOKEN"])

