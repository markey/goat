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
        self.last_idk = None
        self.edbs = {}

    def get_selections_prompt(self, selections):
        return "These are snippets of previous conversations that appear to be related to the current conversation.\n\n{}\n\n".format(
            "".join([f"{i}: {s}\n" for i, s in enumerate(selections)])
        )

    def get_prompt(self, channel, selections):
        history_prompt = self.history.get_formatted_history(channel)
        selections_prompt = self.get_selections_prompt(selections)
        return "{}\n\n{}\nHere is the current conversation.\n{}<{}>:".format(
            self.config.prompt, selections_prompt, history_prompt, self.config.bot_name
        )

    async def should_respond(self, channel):
        history = self.history.get_formatted_history(channel)
        prompt = f"You are goat. You are interested in AI, opportunities to make a joke, and effective accelerationism (e/acc)\n\nPlease rate your interest level in the following conversation by writing a number from 1 to 10.\n\n{history}\n\nINTEREST:"
        # get completion from the curie model
        response = await self.get_completion(prompt, engine="text-curie-001")
        interest = 0
        try:
            interest = int(response.strip())
        except:
            pass
        print(f"{interest=}")
        return interest > 8

    def get_edb(self, guild_id):
        if guild_id not in self.edbs:
            self.edbs[guild_id] = embeddings.EmbeddingDB(
                f"goat_history_{guild_id}", host=self.config.qdrant_host
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
        embedding = await self.get_embedding(history)

        # reply to messages that are replies to goat, or messages that mention his name
        try:
            # message.reference will be None if the message is not a reply
            reply_author = message.reference.cached_message.author.display_name
            # TODO: use the referenced message to construct the embedding.
        except:
            reply_author = None
        # if the message is not directly targeting goat, see if goat wants to respond anyway.
        want_respond = True
        if reply_author != self.config.bot_name and not re.search(
            "goat", message.content, re.I
        ):
            # want_respond = await self.should_respond(channel)
            want_respond = False
            
        if not want_respond:
            edb.add(history, embedding)
            return None

        nearest = edb.get_nearest(embedding, limit=10)
        selections = [i.payload["text"] for i in nearest]

        response = await self.get_response(
            channel, selections, last_response=self.last_response
        )
        response = response.lstrip()
        log.info(f"Got response: {response}")
        if not response:
            # create an idk repsonse
            response = await self.get_idk(self.last_idk)
        self.last_response = response
        self.last_idk = response

        # save goat's response with the previous embedding for the question
        self.history.add(channel, self.config.bot_name, response)
        text = self.get_history(channel)
        log.info(f"Got history for embedding: {text}")
        edb.add(text, embedding)

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

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
    async def get_embedding(self, text):
        return await embeddings.get_embedding(text)

    def get_history(self, channel):
        return self.history.get_formatted_history(channel, 2)

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
    async def get_completion(self, prompt, temperature=None, engine=None):
        if temperature is None:
            temperature = self.config.temperature
        if engine is None:
            engine = self.config.engine
        r = await openai.Completion.acreate(
            engine=engine,
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
    @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
    async def get_idk(self, last_idk=None):
        prompt = "Rephrase the following: I'm not sure what you mean, can you try again?\nRephrase:"
        response = await self.get_completion(prompt)
        if response == last_idk:
            response = await self.get_completion(
                prompt, temperature=self.config.high_temperature
            )
        if response is None:
            response = "I didn't get that, can you say that again?"
        return response
