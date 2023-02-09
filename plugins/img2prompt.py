import base64
from discord.ext import commands
import asyncio
import replicate
import re


class Bot(commands.Cog):
    def __init__(self, bot, config, history):
        self.bot = bot
        self.config = config
        self.history = history
        # TODO pull name from bot
        self.model = replicate.models.get("methexis-inc/img2prompt")

    @commands.Cog.listener()
    async def on_message(self, message):
        channel = message.channel.name
        author = message.author.name
        content = message.content

        # don't respond to my own message events
        # TODO: update to unique IDs
        if author == self.config.bot_name:
            return None

        # respond when triggered
        if not re.search("^goat,? look( at)?", content, re.I):
            return None

        # extract any listed urls from the message
        url = None
        urls = re.findall(r"(https?://[^\s]+)", content)
        if urls:
            url = urls[0]
        elif message.attachments:
            url = message.attachments[0].url
        if not url:
            await message.reply("I need an image to look at.")

        # acknowledge the request with a reaction
        await message.add_reaction("👀")

        print("Running img2prompt")
        # this request will take >20seconds typically.
        prediction = replicate.predictions.create(
            version=self.model.versions.list()[0],
            input={
                "image": url,
            },
        )
        while prediction.status not in ["succeeded", "failed", "canceled"]:
            prediction.reload()
            print(f"Waiting for img2prompt: {url}")
            await asyncio.sleep(1.0)

        if prediction.status == "succeeded":
            await message.reply(prediction.output)
        else:
            print(
                "I tried to look at it, but I got status {}".format(prediction.status)
            )
            await message.reply("I couldn't see anything.")
