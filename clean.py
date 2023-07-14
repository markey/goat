import util.config
import chromadb
from chromadb.config import Settings

config = util.config.Config()

client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory=config.chromadb_directory,
    anonymized_telemetry=False
))

client.reset()
