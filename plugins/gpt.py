from collections import defaultdict, deque, namedtuple
import collections
from discord.ext import commands
import openai
import random
import re

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

class Bot(commands.Cog):
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.history = MessageHistory(self.config.history_length)
        self.last_response = None
        # autocrat: added this for for non-response messages
        self.last_idk = None

    def get_prompt(self, messages):
        log = []
        for m in messages:
            log.append("### <{}>: {}\n".format(m.author, m.text))
        log_message = "".join(log)

        prompt = """{}

{}
### <{}>:"""

        return prompt.format(self.config.prompt, log_message, self.config.bot_name)

    @commands.Cog.listener()
    async def on_message(self, message):
        # autocrat: maybe use channel id to account for repeat channel names accross servers?
        channel = message.channel.name
        author = message.author.name
        content = message.content

        # TODO: move debug messages to message history.
        print("{} {}: {}".format(channel, author, content))

        # don't respond to my own message events
        # TODO: update to unique IDs

        if author == self.config.bot_name:
            return None

        # update history with current discussion.
        self.history.add(channel, author, content)

        # filter out other commands -- TODO: fix this.
        if re.search("^goat (draw|look)", content, re.I):
            return None

        # autocrat: added this for goat to repond when people reply to him
        # respond when replied to
        if message.reference:
            parent_message = message.reference.cached_message

            if parent_message.author.name == self.config.bot_name:
                response = await self.get_response(channel)

                if response == parent_message.content:
                    # if goat is repeating, then turn up the temperature
                    response = await self.get_response(channel, temperature=self.config.high_temperature)
                if response:
                    await message.channel.send(response)
                    self.last_response = response
                    self.history.add(channel, self.config.bot_name, response)
                    # how should this be handled?
                    return True
                else: 
                    # create an idk repsonse
                    response = await self.get_idk()

                    if response == self.last_idk:
                        # if goat is repeating, then turn up the temperature
                        response = await self.get_idk(temperature=self.config.high_temperature)
                    if response:
                        await message.channel.send(response)
                        self.last_idk = response
                        # not sure if this should be added to history
                        # self.history.add(channel, self.config.bot_name, response)
                        return True
                    else: 
                        await message.channel.send("I'm not sure what you're trying to say, can you repeat that?")
                        return True
            else: 
                # not sure about this — removes goat query for ppl replying to eachother
                return None

        # don't respond when not mentioned or replied to
        if not re.search("goat", content, re.I):
            return None


        response = await self.get_response(channel)
        if response == self.last_response:
            # if goat is repeating, then turn up the temperature to try to
            # break the cycle
            # TODO: this should be server and channel specific.
            response = await self.get_response(channel, temperature=self.config.high_temperature)
        if response:
            await message.channel.send(response)
            # record the bots outgoing response in history.
            self.last_response = response
            self.history.add(channel, self.config.bot_name, response)
            # autocrat: added for symetry
            return True
        # autocrat: added idk repsonse 
        else:
            # create an 'idk' repsonse
                    response = await self.get_idk()

                    if response == self.last_idk:
                        # if goat is repeating, then turn up the temperature
                        response = await self.get_idk(temperature=self.config.high_temperature)
                    if response:
                        await message.channel.send(response)
                        self.last_idk = response
                        # not sure if this should be added to history
                        # self.history.add(channel, self.config.bot_name, response)
                        return True
                    else: 
                        await message.channel.send("I'm not sure what you're trying to say, can you repeat that?")
                        return True



    async def get_response(self, channel, temperature=None):
        # TODO: verify prompt length is limited to the correct
        # number of tokens.
        prompt = self.get_prompt(self.history.get(channel))

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



