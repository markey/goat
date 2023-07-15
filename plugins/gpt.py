from collections import defaultdict, namedtuple
from discord.ext import commands
import openai
import re
import glog as log
from tenacity import retry, stop_after_attempt, wait_fixed

from plugins.lib import embeddings


class Bot(commands.Cog):
    def __init__(self, bot, config, history):
        self.bot = bot
        self.config = config
        self.history = history
        self.last_response = None
        # autocrat: added this for for non-response messages
        self.edbs = {}

    def get_selections_prompt(self, selections):
        return "These are snippets of previous conversations that appear to be related to the current conversation:\n\n{}\n\n".format(
            "".join([f"{i}:\n{s}\n" for i, s in enumerate(selections)])
        )

    def get_prompt(self, channel, selections):
        history_prompt = self.history.get_formatted_history(channel)
        selections_prompt = self.get_selections_prompt(selections)
        return "{}\nHere is the current conversation:\n\n{}<{}>:".format(
            selections_prompt, history_prompt, self.config.bot_name
        )

    def get_edb(self, guild_id):
        if guild_id not in self.edbs:
            self.edbs[guild_id] = embeddings.EmbeddingDB(
                f"goat_history_{guild_id}"
            )

        return self.edbs[guild_id]

    @commands.Cog.listener()
    async def on_message(self, message):
        # TODO: autocrat: maybe use channel id to account for repeat channel names accross servers?
        channel = message.channel.name
        author = message.author.display_name

        # don't respond to my own message events
        if author == self.config.bot_name:
            return None

        # filter out messages from other bots
        if message.author.bot:
            return None

        if message.content == "":
            return None

        # filter out messages that are targeted toward other bots
        if re.search(f"^(!|>>)", message.content):
            return None

        # filter out other commands
        # TODO: fix this with better command dispatching.
        if re.search("^goat,? (draw|look)", message.content, re.I):
            return None

        # add message to history--this is required to happen first so embedding lookups work.
        m = self.history.add_message(message)

        edb = self.get_edb(message.guild.id)
        history = self.get_history(channel)

        # reply to messages that are replies to goat, or messages that mention his name
        want_reply = False
        if re.search(self.config.bot_name, message.content, re.I):
            log.info("Replying to: {}".format(message.content))
            want_reply = True

        msg_reply = None
        if message.reference is not None:
            ref = message.reference
            if ref.cached_message is not None:
                msg_reply = ref.cached_message
            else:
                msg_reply = await message.channel.fetch_message(ref.message_id)

            if msg_reply is not None:
                if msg_reply.author.display_name.lower() == self.config.bot_name.lower():
                    want_reply = True

        # if we don't want to reply, then just add the message to the history and return
        if want_reply == False:
            edb.add(history)
            log.info("Early return")
            return None

        nearest = edb.get_nearest(history, limit=10)
        selections = nearest["documents"][0]

        response = await self.get_response(
            channel, selections, last_response=self.last_response
        )
        response = response.lstrip()
        log.info(f"Got response: {response}")
        self.last_response = response

        # save goat's response with the previous embedding for the question
        self.history.add(channel, self.config.bot_name, response)
        text = self.get_history(channel)
        log.info(f"Got history for embedding: {text}")
        edb.add(text)

        await message.channel.send(response)

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
    async def get_response(self, channel, selections, last_response=None):
        # TODO: verify prompt length is limited to the correct
        # number of tokens.
        prompt = self.get_prompt(channel, selections)
        log.info(prompt)
        response = await self.get_completion(prompt)
        if response == last_response:
            response = await self.get_completion(
                prompt, temperature=self.config.high_temperature
            )
        return response

    def get_history(self, channel):
        return self.history.get_formatted_history(channel, 2)

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
    async def get_completion(self, prompt, temperature=None, engine=None):
        if temperature is None:
            temperature = self.config.temperature
        if engine is None:
            engine = self.config.engine
        r = await openai.ChatCompletion.acreate(
            model=engine,
            messages=[
                {"role": "system", "content": self.config.prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=self.config.max_tokens,
            top_p=self.config.top_p,
            frequency_penalty=self.config.frequency_penalty,
            presence_penalty=self.config.presence_penalty,
            stop="<",
        )
        return r["choices"][0]["message"]["content"]
