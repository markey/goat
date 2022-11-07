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


def get_prompt(channel, messages):
    log = []
    for m in messages:
        log.append("<{}>: {}\n".format(m.author, m.text))
    log_message = "".join(log)

    prompt_template = """
    Goat is a unique and brilliant goat who has learned how to use the internet. He is helpful, curious, sarcastic and opinionated.

Here is one of his chats:

{}
<goat>:"""

    return prompt_template.format(log_message)


class Bot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # TODO pull name from bot
        self.name = BOT_NAME
        self.history = MessageHistory(20)
        self.last_response = None
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

        # filter out other commands -- TODO: fix this.
        if re.search("^goat (draw|look)", content, re.I):
            return None

        # respond when mentioned
        if not re.search("goat", content, re.I):
            return None

        response = await self.get_response(channel, author, content)
        if response == self.last_response:
            # if goat is repeating, then turn up the temperature to try to
            # break the cycle
            response = await self.get_response(channel, author, content,
                                               temperature=0.99)
        if response:
            # clean response if goat tries to hallucinate a whole conversation.
            match = re.search(r"<[^>]+>:", response)
            if match:
                print("Cleaning: {}".format(response))
                response = response[:match.start()]
            await message.channel.send(response)
            # record the bots outgoing response in history.
            self.last_response = response
            self.history.add(channel, self.name, response)


    async def get_response(self, channel, author, text, temperature=0.9):
        # TODO: verify prompt length is limited to the correct
        # number of tokens.
        prompt = get_prompt(channel, self.history.get(channel))

        r = openai.Completion.create(
            # $0.06/1000 tokens, max 4096 tokens/req
            #engine="text-davinci-002",
            # some people have said davinci-001 is better conversationally.
            engine="text-davinci-001",

            # 0.006/1000, max 2048 tokens/req
            #engine="text-curie-001",
            prompt=prompt,
            temperature=temperature,
            max_tokens=150,
            top_p=1,
            frequency_penalty=0.025,
            presence_penalty=0.6,
        )
        return r.choices[0].text


