import discord
from discord.ext import commands
import markovify

BOT_NAME = "goat"

class Bot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.name = BOT_NAME
        self.models = dict()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.name == self.name:
            return

        # generate if needed
        #TODO: convert this to a commands.command
        if message.content.startswith("goatov"):
            try:
                model = self.models[message.guild]
            except KeyError:
                pass
            else:
                # this can fail if it can't create interesting enough
                # sentences.
                response = model.make_short_sentence(280)
                if response:
                    await message.channel.send(response)
        else:
            # update models
            new_model = markovify.Text(message.content)
            try:
                model = self.models[message.guild]
            except KeyError:
                self.models[message.guild] = new_model
            else:
                combined_model = markovify.combine([model, new_model])
                self.models[message.guild] = combined_model
