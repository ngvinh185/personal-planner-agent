from collections.abc import Sequence

from langgraph.store.base import IndexConfig
from langgraph.store.postgres import PostgresStore  # type: ignore[import-not-found]
from langchain_huggingface import HuggingFaceEmbeddings

DB_URI = "postgresql://postgres:010805@localhost:5432/postgres?sslmode=disable"

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def setup_postgres_store():
    return PostgresStore.from_conn_string(
        DB_URI,
        index=IndexConfig(
            embed=embeddings,
            dims=384,  # dims của all-MiniLM-L6-v2
            fields=["content"],
        ),
    )