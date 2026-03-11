import os
from dotenv import load_dotenv

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = int(os.getenv("QDRANT_PORT"))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION")
VECTOR_SIZE = int(os.getenv("QDRANT_VECTOR_SIZE"))


def init_qdrant():
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]

    # Checks if the collection already exists in the database. In case it does
    # not exist, the collection is created
    if COLLECTION_NAME not in collection_names:
        print(f"Creating collection: {COLLECTION_NAME}")

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )

        print("Collection created!")
    else:
        print("Collection already exists")
