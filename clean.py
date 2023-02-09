import util.config
import json
from qdrant_client import QdrantClient

api_key = json.load(open("qdrant_secrets.json"))["api_key"]

# get qdrant host from config
config = util.config.Config()
qdrant_host = config.qdrant_host

client = QdrantClient(host=qdrant_host, api_key=api_key)

# list collections
resp = client.get_collections()
print(f"{resp=}")

for collection in resp.collections:
    # delete any collections that start with the name "goat_history"
    if collection.name.startswith("goat_history"):
        print(f"deleting {collection}")
        dresp = client.delete_collection(collection_name=collection.name)
        print(dresp)
