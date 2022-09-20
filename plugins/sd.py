from discord.ext import commands
import asyncio
import replicate
import re

BOT_NAME = "goat"

class Bot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # TODO pull name from bot
        self.name = BOT_NAME
        self.model = replicate.models.get("stability-ai/stable-diffusion")


    @commands.Cog.listener()
    async def on_message(self, message):
        channel = message.channel.name
        author = message.author.name
        content = message.content

        # don't respond to my own message events
        # TODO: update to unique IDs
        if author == self.name:
            return None

        # respond when triggered
        if not re.search("^goat draw ", content, re.I):
            return None

        prompt = content[10:]
        print("Requesting image for: ", prompt)
        prediction = replicate.predictions.create(
            version=self.model.versions.list()[0],
            input={
                "prompt": prompt,
            })
        while prediction.status not in ["succeeded", "failed", "canceled"]:
            prediction.reload()
            print("Waiting for {}".format(prompt))
            await asyncio.sleep(0.5)

        if prediction.status == "succeeded":
            await message.channel.send("{}\n{}".format(prompt, prediction.output[0]))
        else:
            print("Got status {} for {}".format(prediction.status, prompt))
            await message.channel.send("I failed to draw {}".format(prompt))
