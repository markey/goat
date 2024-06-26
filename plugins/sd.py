from discord.ext import commands
import asyncio
import replicate
import re


class SdBot(commands.Cog):
    def __init__(self, bot, config, history):
        self.bot = bot
        self.config = config
        self.history = history
        self.model = replicate.models.get("stability-ai/sdxl")

    @commands.Cog.listener()
    async def on_message(self, message):
        author = message.author.name
        content = message.content

        # don't respond to my own message events
        if author == self.config.bot_name:
            return None

        # respond when triggered
        r = re.match(f"^{self.config.bot_name},? draw:? (me |a picture of )?(.+)", content, re.I)
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
            await asyncio.sleep(1)

        if prediction.status == "succeeded":
            response = "{}\n{}".format(prompt, prediction.output[0])
        else:
            print("Got status {} for {}".format(prediction.status, prompt))
            response = "I couldn't draw that."

        await message.reply(response)
