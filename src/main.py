from flask import Flask
from dotenv import load_dotenv
import os

from src.db.db_init import init_qdrant, init_redis

# from src.db.redis_seeder import seed_redis
from src.core.vector import vectorize_entries
from src.api.match import match_bp, init_matcher
from sentence_transformers import SentenceTransformer

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.config["JSON_AS_ASCII"] = False

    qdrant_collection = os.getenv("QDRANT_COLLECTION", "precedents")
    model_name = os.getenv("MODEL_NAME", "all-MiniLM-L6-v2")

    print("Initializing databases...")
    qdrant_client = init_qdrant()
    redis_client = init_redis()

    # if redis_client:
    #     print("Seeding Redis...")
    #     seed_redis(redis_client)

    print("Loading model and vectorizing data...")
    model = SentenceTransformer(model_name)

    vectorize_entries(redis_client, qdrant_client, qdrant_collection, model)

    print("Initializing matcher...")
    init_matcher(qdrant_client, qdrant_collection, model_name)

    app.register_blueprint(match_bp, url_prefix="/api")

    return app


if __name__ == "__main__":
    app = create_app()

    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    print(f"Starting Flask server on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=debug)
