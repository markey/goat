import asyncio
import json
import os

import discord
import glog as log
from discord.ext import commands

import util.config
import util.history
from plugins import gpt

config = util.config.Config()
history = util.history.MessageHistory(config.history_length)

my_intents = discord.Intents.default()
my_intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=my_intents)

@bot.event
async def on_ready():
    print("Ready!")

async def setup():
    for cog in [gpt]:
        await bot.add_cog(cog.Bot(bot, config, history))
        log.info(f"Loaded cog {cog.__name__}")

asyncio.run(setup())

bot.run(os.environ["DISCORD_TOKEN"])
