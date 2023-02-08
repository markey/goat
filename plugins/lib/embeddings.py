import json
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, Distance, UpdateStatus, VectorParams
import openai

import glog as log


def get_qdrant_api_key():
    with open("qdrant_secrets.json") as f:
        secrets = json.load(f)
    return secrets["api_key"]


async def get_embedding(text):
    text = text.replace("\n", " ")
    try:
        r = await openai.Embedding.acreate(input=[text], model="text-embedding-ada-002")
    except openai.OpenAIError as e:
        log.info(f"Error getting embedding: {e}")
        return

    try:
        embedding = r["data"][0]["embedding"]
    except (KeyError, IndexError) as e:
        log.error(f"Error getting embedding: {e}")
        return
    return embedding


class EmbeddingDB:
    def __init__(self, collection_name, host, port=6333):
        self.api_key = get_qdrant_api_key()
        self.client = QdrantClient(
            host=host,
            port=port,
            api_key=self.api_key,
        )
        self.collection_name = collection_name

        collections = self.client.get_collections()
        log.info("Collections: " + str(collections))
        # see if our collection_name exists
        exists = False
        for collection in collections.collections:
            if collection.name == self.collection_name:
                exists = True
                break
        if not exists:
            self._create_collection()
        collection_info = self.client.get_collection(
            collection_name=self.collection_name
        )
        log.info("Collection info: " + str(collection_info))

    def _create_collection(self):
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )

    def add(self, text, embedding):
        # generate a random uuid, for whatever reason qdrant doesn't seem to handle autogenerating
        # ids for us.
        id = str(uuid.uuid4())

        operation_info = self.client.upsert(
            collection_name=self.collection_name,
            wait=True,
            points=[PointStruct(id=id, vector=embedding, payload={"text": text})],
        )
        assert operation_info.status == UpdateStatus.COMPLETED

    def get_nearest(self, embedding, limit=1):
        search_result = self.client.search(
            collection_name=self.collection_name,
            limit=limit,
            query_vector=embedding,
        )
        return search_result

    def reset(self):
        self.client.delete_collection(self.collection_name)
        self._create_collection()
