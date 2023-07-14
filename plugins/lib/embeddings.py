import util.config
import uuid
import chromadb
from chromadb.config import Settings
import glog as log


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
            name=self.collection_name
        )

    def add(self, text):
        # generate a random uuid
        id = str(uuid.uuid4())

        self.collection.upsert(
            ids=[id], documents=[text]
        )

    def get_nearest(self, text, limit=1):
        search_result = self.collection.query(
            n_results=limit,
            query_texts=[text]
        )
        log.info(f"Got search result: {search_result}")
        return search_result
