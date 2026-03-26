import os
from src.db.db_init import init_qdrant, init_redis
from src.db.redis_seeder import seed_redis
from src.core.vector import vectorize_entries
from dotenv import load_dotenv

load_dotenv()

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION")

if __name__ == "__main__":
    print("Inilializing Database")
    qdrant_client = init_qdrant()

    redis_client = init_redis()

    if redis_client:
        seed_redis(redis_client)

    vectorize_entries(redis_client, qdrant_client, COLLECTION_NAME)
