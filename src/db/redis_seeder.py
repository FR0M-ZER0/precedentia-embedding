from datetime import datetime, timedelta
import random


def random_past_date():
    days_ago = random.randint(1, 730)
    random_date = datetime.now() - timedelta(days=days_ago)

    return random_date.strftime("%Y-%m-%d %H:%M:%S")


def seed_redis(redis_client):
    precedents = [
        {
            "id": 1,
            "name": "Tema 123 STF",
            "tribunal": "STF",
            "last_update": random_past_date(),
            "situation": "Ativo",
            "url": "https://stf.jus.br/tema123",
            "description": (
                "Discussão sobre constitucionalidade de tributos estaduais."
            ),
        },
        {
            "id": 2,
            "name": "Tema 456 STJ",
            "tribunal": "STJ",
            "last_update": random_past_date(),
            "situation": "Ativo",
            "url": "https://stj.jus.br/tema456",
            "description": "Responsabilidade civil em contratos bancários.",
        },
        {
            "id": 3,
            "name": "Tema 789 STF",
            "tribunal": "STF",
            "last_update": random_past_date(),
            "situation": "Suspenso",
            "url": "https://stf.jus.br/tema789",
            "description": "Validade de normas ambientais estaduais.",
        },
        {
            "id": 4,
            "name": "Tema 321 STJ",
            "tribunal": "STJ",
            "last_update": random_past_date(),
            "situation": "Finalizado",
            "url": "https://stj.jus.br/tema321",
            "description": "Execução fiscal e prescrição intercorrente.",
        },
        {
            "id": 5,
            "name": "Tema 654 STF",
            "tribunal": "STF",
            "last_update": random_past_date(),
            "situation": "Ativo",
            "url": "https://stf.jus.br/tema654",
            "description": "Direitos fundamentais e liberdade de expressão.",
        },
    ]

    for p in precedents:
        key = f"precedent:{p['id']}"

        redis_client.hset(
            key,
            mapping={
                "name": p["name"],
                "tribunal": p["tribunal"],
                "last_update": p["last_update"],
                "situation": p["situation"],
                "url": p["url"],
                "description": p["description"],
            },
        )

    print("Redis seeded successfully!")
