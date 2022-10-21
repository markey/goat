from discord.ext import commands
from plugins import gpt, sd, img2prompt
import os

BOT_NAME = "goat"

bot = commands.Bot(command_prefix="!")
@bot.event
async def on_ready():
    print("Ready!")

for cog in [gpt, sd, img2prompt]:
    bot.add_cog(cog.Bot(bot))

bot.run(os.environ["DISCORD_TOKEN"])

