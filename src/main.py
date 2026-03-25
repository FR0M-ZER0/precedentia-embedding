from src.db.db_init import init_qdrant, init_redis
from src.db.redis_seeder import seed_redis


if __name__ == "__main__":
    print("Inilializing Database")
    init_qdrant()

    redis_client = init_redis()

    if redis_client:
        seed_redis(redis_client)
