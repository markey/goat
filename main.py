from discord.ext import commands
from plugins import gpt, sd, img2prompt
import json
import os

import util.history
import util.config


config = util.config.Config()

bot = commands.Bot(command_prefix="!")


@bot.event
async def on_ready():
    print("Ready!")


history = util.history.MessageHistory(config.history_length)
for cog in [gpt, sd, img2prompt]:
    bot.add_cog(cog.Bot(bot, config, history))

bot.run(os.environ["DISCORD_TOKEN"])
