from collections import defaultdict, deque, namedtuple
import collections
from discord.ext import commands
import openai
import random
import re
import glog as log

from .lib import embeddings


# TODO add server to message history for multi server support.
# TODO convert these things to real identifiers
Message = namedtuple("Message", ["channel", "author", "text"])


def format_message(m):
    return f"<{m.author}>: {m.text}"


class MessageHistory:
    def __init__(self, history_length):
        def get_deq():
            return deque(list(), history_length)

        self.history = defaultdict(get_deq)

    def add(self, channel, author, text):
        m = Message(channel, author, text)
        self.history[channel].append(m)
        return m

    def get(self, channel):
        return list(self.history[channel])


class Bot(commands.Cog):
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.history = MessageHistory(self.config.history_length)
        self.last_response = None
        # autocrat: added this for for non-response messages
        self.last_idk = None
        self.edbs = {}

    def get_selections_prompt(self, selections):
        return "As a reminder, here are some selections from previous conversations.\n\n{}\n\n".format(
            "".join([f"{i}: {s}\n" for i, s in enumerate(selections)])
        )

    def get_history_prompt(self, messages):
        return "".join([f"<{m.author}>: {m.text}\n" for m in messages])

    def get_prompt(self, channel, selections):
        messages = self.history.get(channel)
        # TODO incorporate channel here
        history_prompt = self.get_history_prompt(messages)
        selections_prompt = self.get_selections_prompt(selections)
        return "{}\n\nHere are some relevent bits of conversation.\n\n{}\nHere is a chat log.\n{}<{}>:".format(
            self.config.prompt, selections_prompt, history_prompt, self.config.bot_name
        )

    def get_edb(self, guild_id):
        if guild_id not in self.edbs:
            self.edbs[guild_id] = embeddings.EmbeddingDB(f"goat_history_{guild_id}")
        return self.edbs[guild_id]

    async def get_selections(self, msg, guild_id):
        """Get a list of selections from the history to use as a prompt for the current message."""
        # get recent messages from history and pair them with the current message.

        messages = self.history.get(msg.channel)[-3:]
        history = "".join([f"<{m.author}>: {m.text}\n" for m in messages])
        full_text = f"{history}\n"

        edb = self.get_edb(guild_id)
        embedding = await embeddings.get_embedding(full_text)
        nearest = edb.get_nearest(embedding, limit=10)
        edb.add(full_text, embedding)
        return nearest

    @commands.Cog.listener()
    async def on_message(self, message):
        # autocrat: maybe use channel id to account for repeat channel names accross servers?
        channel = message.channel.name
        author = message.author.name
        content = message.content

        # don't respond to my own message events
        # TODO: update to unique IDs
        if author == self.config.bot_name:
            return None

        # filter out messages from other bots
        if message.author.bot:
            return None

        if content == "":
            return None

        # filter out messages that are targeted toward other bots
        if re.search(f"^(!|>>)", content):
            return None

        # update history with current discussion.
        m = self.history.add(channel, author, content)
        log.info(format_message(m))

        # filter out other commands
        # TODO: fix this with better command dispatching.
        if re.search("^goat,? (draw|look)", content, re.I):
            return None

        # reply to messages that are replies to goat, or messages that mention his name
        reply_author = None
        if message.reference:
            if message.reference.cached_message is not None:
                reply_author = message.reference.cached_message.author.name
        if reply_author != self.config.bot_name and not re.search(
            "goat", content, re.I
        ):
            return None

        # get useful context from EmbeddingDB and save new conversational embeddings
        selections = await self.get_selections(m, message.guild.id)

        msg = format_message(m)
        embedding = await embeddings.get_embedding(msg)
        self.get_edb(message.guild.id).add(msg, embedding)

        response = await self.get_response(channel, selections)

        if response == self.last_response:
            # if goat is repeating, then turn up the temperature
            response = await self.get_response(
                channel, temperature=self.config.high_temperature
            )
        if not response:
            # create an idk repsonse
            response = await self.get_idk()

            if response == self.last_idk:
                # if goat is repeating, then turn up the temperature
                response = await self.get_idk(temperature=self.config.high_temperature)

            if not response:
                response = (
                    "I'm not sure what you're trying to say, can you repeat that?"
                )

        await message.channel.send(response)
        self.last_idk = response
        self.history.add(channel, self.config.bot_name, response)

        # add response to edb as well
        # TODO: update this to multi-line embeddings
        edb = self.get_edb(message.guild.id)
        msg = format_message(m)
        embedding = await embeddings.get_embedding(msg)
        edb.add(msg, embedding)

    async def get_response(self, channel, selections, temperature=None):
        # TODO: verify prompt length is limited to the correct
        # number of tokens.
        prompt = self.get_prompt(channel, selections)
        log.info(prompt)

        if temperature is None:
            temperature = self.config.temperature

        r = openai.Completion.create(
            engine=self.config.engine,
            prompt=prompt,
            temperature=temperature,
            max_tokens=self.config.max_tokens,
            top_p=self.config.top_p,
            frequency_penalty=self.config.frequency_penalty,
            presence_penalty=self.config.presence_penalty,
            stop="<",
        )
        return r.choices[0].text

    # autocrat: added this to create an idk response, don't think it works but you get the idea
    async def get_idk(self, temperature=None):
        prompt = "repeat this in your own words: 'I'm not sure what you mean, can you try again?'"

        if temperature is None:
            temperature = self.config.temperature

        r = openai.Completion.create(
            engine=self.config.engine,
            prompt=prompt,
            temperature=temperature,
            max_tokens=self.config.max_tokens,
            top_p=self.config.top_p,
            frequency_penalty=self.config.frequency_penalty,
            presence_penalty=self.config.presence_penalty,
            stop="###",
        )
        return r.choices[0].text
