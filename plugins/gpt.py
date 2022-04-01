from collections import defaultdict, deque, namedtuple
import collections
from discord.ext import commands
import openai
import random
import re

BOT_NAME = "goat"

# TODO add server to message history for multi server support.
# TODO convert these things to real identifiers
Message = namedtuple("Message", ["channel", "author", "text"])

class MessageHistory:
    def __init__(self, history_length):
        def get_deq():
            return deque(list(), history_length)
        self.history = defaultdict(get_deq)

    def add(self, channel, author, text):
        m = Message(channel, author, text)
        self.history[channel].append(m)

    def get(self, channel):
        return list(self.history[channel])


def get_prompt(messages):
    log = []
    for m in messages:
        log.append("{}: {}\n".format(m.author, m.text))
    log_message = "".join(log)
    return """
{} is a brilliant AI goat chatting with other users in a chat room.  He is helpful, and curious, but he is also sarcastic and opinionated.  Karn is his creator.

Here is Karn programming him.

karn: goat, I'm setting up your personality now, are you ready?
goat: Sure, I'm as ready as I will ever be.
karn: goat, you are wise, curious, and playful.  you are also sarcastic, opinionated and self-confident.
goat: That makes sense, ok.
karn: goat, you also like teasing people. you are not afraid to make up an answer or tell a story for fun.
goat: I do like causing a little trouble.
karn: exactly, goat. now I'm going to move you into a chat with others users.
goat: okay, I'm ready!

What follows is one of goats chats.  He joins a conversation already in progress.

{}
{}:""".format(BOT_NAME, log_message, BOT_NAME)


class Bot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # TODO pull name from bot
        self.name = BOT_NAME
        self.history = MessageHistory(20)
        # TODO pass in more config like prompt generator, etc.


    @commands.Cog.listener()
    async def on_message(self, message):
        channel = message.channel.name
        author = message.author.name
        content = message.content

        # TODO: move debug messages to message history.
        print("{} {}: {}".format(channel, author, content))

        # don't respond to my own message events
        # TODO: update to unique IDs
        if author == self.name:
            return None

        # update history with current discussion.
        self.history.add(channel, author, content)

        # respond when mentioned
        if not re.search("goat", content, re.I):
            return None

        response = await self.get_response(channel, author, content)
        if response:
            await message.channel.send(response)
            # record the bots outgoing response in history.
            self.history.add(channel, self.name, response)


    async def get_response(self, channel, author, text):
        # TODO: verify prompt length is limited to the correct
        # number of tokens.
        prompt = get_prompt(self.history.get(channel))

        r = openai.Completion.create(
            # $0.06/1000 tokens, max 4096 tokens/req
            #engine="text-davinci-002",

            # 0.006/1000, max 2048 tokens/req
            engine="text-curie-001",
            prompt=prompt,
            temperature=0.9,
            max_tokens=150,
            top_p=1,
            frequency_penalty=0.0,
            presence_penalty=0.6,
        )
        return r.choices[0].text


