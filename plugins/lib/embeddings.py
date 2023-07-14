import json
import util.config
import uuid
import openai
import chromadb
from chromadb.config import Settings
import glog as log


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
    def __init__(self, collection_name):
        config = util.config.Config()

        self.collection_name = collection_name

        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=config.chromadb_directory,
            anonymized_telemetry=False
        ))

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"})

    # def _create_collection(self):
    #     self.client.recreate_collection(
    #         collection_name=self.collection_name,
    #         vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    #     )

    def add(self, text, embedding):
        # generate a random uuid, for whatever reason qdrant doesn't seem to handle autogenerating
        # ids for us.
        id = str(uuid.uuid4())

        self.collection.upsert(
            ids=[id], embeddings=[embedding], documents=[text]
        )

    def get_nearest(self, embedding, limit=1):
        search_result = self.collection.query(
            n_results=limit,
            query_embeddings=[embedding]
        )
        log.info(f"Got search result: {search_result}")
        return search_result
