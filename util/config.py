import json


class Config:
    def __init__(self, filename="config.json"):
        with open("config.json") as f:
            self.config = json.load(f)

    def __getattr__(self, key):
        return self.config[key]
