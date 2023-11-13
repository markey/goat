from collections import namedtuple, defaultdict
import glog as log

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

    def add_message(self, message):
        """Takes a discord message object and adds it to the history."""
        self.add(message.channel.name, message.author.display_name, message.content)

    def get(self, channel):
        return list(self.history[channel])

    def get_formatted_history(self, channel, length=None):
        if length is None:
            length = self.history_length
        messages = [format_message(m) for m in self.history[channel][-length:]]
        if messages:
            last_message = messages.pop()
            return "\n".join(messages) + "\n\n" + last_message + "\n"
        else:
            return "\n"
        