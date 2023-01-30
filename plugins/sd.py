from discord.ext import commands
import asyncio
import replicate
import re


class Bot(commands.Cog):
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.model = replicate.models.get("cjwbw/stable-diffusion-v2")

    @commands.Cog.listener()
    async def on_message(self, message):
        author = message.author.name
        content = message.content

        # don't respond to my own message events
        # TODO: update to unique IDs
        if author == self.config.bot_name:
            return None

        # respond when triggered
        r = re.match("^goat,? draw:? (me |a picture of )?(.+)", content, re.I)
        if not r:
            return None

        await message.add_reaction("✏️")

        prompt = r.groups()[1]
        print("Requesting image for: ", prompt)
        prediction = replicate.predictions.create(
            version=self.model.versions.list()[0], input={"prompt": prompt}
        )
        while prediction.status not in ["succeeded", "failed", "canceled"]:
            prediction.reload()
            print("Waiting for {}".format(prompt))
            await asyncio.sleep(0.5)

        if prediction.status == "succeeded":
            await message.reply("{}\n{}".format(prompt, prediction.output[0]))
        else:
            print("Got status {} for {}".format(prediction.status, prompt))
            await message.reply("I couldn't draw that.")
