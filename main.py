from collections import defaultdict, deque, namedtuple
import collections
import discord
from discord.ext import commands
import openai
import os
import random
import re

BOT_NAME = "goat"

# TODO add server to message history for multi server support.
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

# global state yolo
history = MessageHistory(20)

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

def get_response(channel, author, text):
    # don't respond to my own message events
    if author == BOT_NAME:
        return None

    # update history with current discussion.
    history.add(channel, author, text)

    # respaond 5% of the time, or when addressed.
    if not re.search("goat", text, re.I) and not random.random() < 0.00:
        return None

    # TODO: verify prompt length is limited to the correct number of tokens.
    prompt = get_prompt(history.get(channel))

    r = openai.Completion.create(
        #engine="text-davinci-002",  $0.06/1000 tokens, 4096 toksns/req
        engine="text-curie-001",     # 0.006/1000, 2048 tokens/req
        prompt=prompt,
        temperature=0.9,
	max_tokens=150,
	top_p=1,
	frequency_penalty=0.0,
	presence_penalty=0.6,
	#stop=[" Human:", " AI:"]
    )
    response = r.choices[0].text
    history.add(channel, BOT_NAME, response)
    return response

class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        print("{} {}: {}".format(
            message.channel.name,
            message.author.name,
            message.content))
        response = get_response(
            message.channel.name,
            message.author.name,
            message.content)
        if response:
            await message.channel.send(response)

 
bot = commands.Bot(command_prefix="!")
 
@bot.event
async def on_ready():
    print("Ready!")

bot.add_cog(Chat(bot))
 
bot.run(os.environ["DISCORD_TOKEN"])

