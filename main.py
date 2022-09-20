from discord.ext import commands
from plugins import gpt, sd
import os

BOT_NAME = "goat"

bot = commands.Bot(command_prefix="!")
@bot.event
async def on_ready():
    print("Ready!")

bot.add_cog(gpt.Bot(bot))
bot.add_cog(sd.Bot(bot))

bot.run(os.environ["DISCORD_TOKEN"])

