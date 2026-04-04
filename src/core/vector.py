from qdrant_client.models import PointStruct


def vectorize(model, key, value):
    text = f"{value.get('name')}. {value.get('description')}"

    vector = model.encode(text).tolist()

    payload = {
        "name": value.get("name"),
        "description": value.get("description"),
        "tribunal": value.get("tribunal"),
        "species": value.get("species"),
        "situation": value.get("situation"),
        "url": value.get("url"),
        "summary": value.get("summary"),
    }

    point_id = int(key.split(":")[1])

    print(f"Entry precedent:{point_id} converted to vector")
    return point_id, vector, payload


def vectorize_entries(redis_client, qdrant_client, qdrant_collection_name, model):
    if redis_client is None:
        raise ValueError("redis_client nao pode ser None")

    if qdrant_client is None:
        raise ValueError("qdrant_client nao pode ser None")

    if not qdrant_collection_name:
        raise ValueError("qdrant_collection_name nao pode ser vazio")

    points = []
    all_keys = set()

    for pattern in ("precedent:*", "precedente:*"):
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor=cursor, match=pattern)
            all_keys.update(keys)

            if cursor == 0:
                break

    skipped_wrong_type = 0
    skipped_invalid_key = 0

    for key in all_keys:
        key_type = redis_client.type(key)
        if key_type != "hash":
            skipped_wrong_type += 1
            continue

        value = redis_client.hgetall(key)

        try:
            point_id, vector, payload = vectorize(model, key, value)
        except (IndexError, ValueError):
            skipped_invalid_key += 1
            continue

        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        )

    if not points:
        print("No precedents found in Redis; skipping Qdrant upsert")
        return

    if skipped_wrong_type:
        print(f"Skipped {skipped_wrong_type} keys with non-hash type")

    if skipped_invalid_key:
        print(f"Skipped {skipped_invalid_key} keys with invalid id format")

    qdrant_client.upsert(
        collection_name=qdrant_collection_name,
        points=points,
    )

    print("Successfully saved all data into Qdrant")
