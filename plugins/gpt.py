from collections import defaultdict, namedtuple
from discord.ext import commands
import openai
import re
import glog as log
from retrying import retry

from .lib import embeddings


# TODO add server to message history for multi server support.
# TODO convert these things to real identifiers
Message = namedtuple("Message", ["channel", "author", "text"])


def format_message(m):
    return f"<{m.author}>: {m.text}"


class MessageHistory:
    def __init__(self, history_length):
        self.history_length = history_length
        self.history = defaultdict(list)

    def add(self, channel, author, text):
        m = Message(channel, author, text)
        log.info(format_message(m))
        self.history[channel].append(m)
        while len(self.history[channel]) > self.history_length:
            self.history[channel].pop(0)
        return m

    def get(self, channel):
        return list(self.history[channel])

    def get_formatted_history(self, channel, length=None):
        if length is None:
            length = self.history_length
        return (
            "\n".join([format_message(m) for m in self.history[channel][-length:]])
            + "\n"
        )


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

    def get_prompt(self, channel, selections):
        messages = self.history.get(channel)
        # TODO incorporate channel here
        history_prompt = self.history.get_formatted_history(channel)
        selections_prompt = self.get_selections_prompt(selections)
        return "{}\n\nHere are some relevent bits of conversation.\n\n{}\nHere is a chat log.\n{}<{}>:".format(
            self.config.prompt, selections_prompt, history_prompt, self.config.bot_name
        )

    def get_edb(self, guild_id):
        if guild_id not in self.edbs:
            self.edbs[guild_id] = embeddings.EmbeddingDB(f"goat_history_{guild_id}")
        return self.edbs[guild_id]

    @commands.Cog.listener()
    async def on_message(self, message):
        # TODO: autocrat: maybe use channel id to account for repeat channel names accross servers?
        channel = message.channel.name
        author = message.author.name

        # don't respond to my own message events
        if author == self.config.bot_name:
            m = self.history.add(channel, author, message.content)
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
        m = self.history.add(channel, author, message.content)

        # reply to messages that are replies to goat, or messages that mention his name
        try:
            # message.reference will be None if the message is not a reply
            reply_author = message.reference.cached_message.author.name
        except:
            reply_author = None
        if reply_author != self.config.bot_name and not re.search(
            "goat", message.content, re.I
        ):
            return None

        # get useful context from EmbeddingDB and save new conversational embeddings
        edb = self.get_edb(message.guild.id)
        _, embedding = await self.get_history_embedding(channel)
        nearest = edb.get_nearest(embedding, limit=10)
        selections = [i.payload["text"] for i in nearest]

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
        self.last_response = response
        self.last_idk = response

        # add outgoing message to history and save goat's response as an embedding.
        self.history.add(channel, self.config.bot_name, response)
        text, embedding = await self.get_history_embedding(channel)
        edb.add(text, embedding)

        await message.channel.send(response)

    @retry(stop_max_attempt_number=3)
    async def get_response(self, channel, selections, temperature=None):
        # TODO: verify prompt length is limited to the correct
        # number of tokens.
        prompt = self.get_prompt(channel, selections)
        log.info(prompt)

        if temperature is None:
            temperature = self.config.temperature

        r = await openai.Completion.acreate(
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

    async def get_history_embedding(self, channel):
        history = self.history.get_formatted_history(channel, 2)
        embedding = await embeddings.get_embedding(history)
        return history, embedding

    # autocrat: added this to create an idk response, don't think it works but you get the idea
    @retry(stop_max_attempt_number=3)
    async def get_idk(self, temperature=None):
        prompt = "Rephrase the following: I'm not sure what you mean, can you try again?\nRephrase:"

        if temperature is None:
            temperature = self.config.temperature

        r = await openai.Completion.create(
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
