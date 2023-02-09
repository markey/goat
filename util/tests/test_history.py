import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from history import MessageHistory


class FakeNamedAttribute:
    def __init__(self, name):
        self.name = name


class FakeMessage:
    def __init__(self, channel, author, content):
        self.channel = FakeNamedAttribute(channel)
        self.author = FakeNamedAttribute(author)
        self.content = content

    def compare(self, msg):
        return (
            self.channel.name == msg.channel
            and self.author.name == msg.author
            and self.content == msg.text
        )


def test_empty_history_get():
    history = MessageHistory(10)
    assert history.get("test") == []


def test_empty_history_get_formatted_history():
    history = MessageHistory(10)
    assert history.get_formatted_history("test") == "\n"


def test_add():
    history = MessageHistory(10)
    m = history.add("test", "author", "text")
    assert history.get("test") == [m]


def test_add_message():
    history = MessageHistory(10)
    msg = FakeMessage("test", "author", "text")
    history.add_message(msg)
    messages = history.get("test")
    assert len(messages) == 1
    assert msg.compare(messages[0])


def test_add():
    history = MessageHistory(10)
    m = history.add("test", "author", "text")
    assert m.channel == "test"
    assert m.author == "author"
    assert m.text == "text"
    messages = history.get("test")
    assert len(messages) == 1
    assert messages[0].channel == "test"
    assert messages[0].author == "author"
    assert messages[0].text == "text"


def test_long_history():
    history = MessageHistory(10)
    for i in range(20):
        history.add("test", "author", f"text {i}")
    messages = history.get("test")
    assert len(messages) == 10
    for i in range(10):
        assert messages[i].channel == "test"
        assert messages[i].author == "author"
        assert messages[i].text == f"text {i + 10}"
