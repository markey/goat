from collections import defaultdict, deque, namedtuple
import collections
import discord
from discord.ext import commands
from plugins import gpt
import markovify
import openai
import os
import random
import re

BOT_NAME = "goat"

 
bot = commands.Bot(command_prefix="!")
 
@bot.event
async def on_ready():
    print("Ready!")

bot.add_cog(gpt.Bot(bot))
 
bot.run(os.environ["DISCORD_TOKEN"])

