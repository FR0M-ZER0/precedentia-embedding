from datetime import datetime, timedelta
import random

TRIBUNALS = ["STF", "STJ", "TST", "TSE", "STM", "TRF1", "TRF2", "TRF3", "TRF4", "TRF5"]

TRIBUNAL_URLS = {
    "STF": "https://stf.jus.br/tema{}",
    "STJ": "https://stj.jus.br/tema{}",
    "TST": "https://tst.jus.br/tema{}",
    "TSE": "https://tse.jus.br/tema{}",
    "STM": "https://stm.jus.br/tema{}",
    "TRF1": "https://trf1.jus.br/tema{}",
    "TRF2": "https://trf2.jus.br/tema{}",
    "TRF3": "https://trf3.jus.br/tema{}",
    "TRF4": "https://trf4.jus.br/tema{}",
    "TRF5": "https://trf5.jus.br/tema{}",
}

DESCRIPTIONS = [
    "Discussão sobre constitucionalidade de tributos estaduais.",
    "Responsabilidade civil em contratos bancários.",
    "Validade de normas ambientais estaduais.",
    "Execução fiscal e prescrição intercorrente.",
    "Direitos fundamentais e liberdade de expressão.",
    "Imunidade tributária de entidades filantrópicas.",
    "Limites do poder regulatório das agências federais.",
    "Aplicação do Código de Defesa do Consumidor em contratos digitais.",
    "Competência jurisdicional em causas envolvendo entes federativos.",
    "Revisão de benefícios previdenciários e critérios de concessão.",
    "Validade de cláusulas arbitrais em contratos de adesão.",
    "Responsabilidade do Estado por omissão em políticas públicas.",
]

SITUATIONS = ["Ativo", "Suspenso", "Finalizado"]
SITUATION_WEIGHTS = [0.6, 0.2, 0.2]


def random_past_date():
    days_ago = random.randint(1, 730)
    random_date = datetime.now() - timedelta(days=days_ago)

    return random_date.strftime("%Y-%m-%d %H:%M:%S")


def random_precedent(entry_id: int, used_theme_numbers: set) -> dict:
    tribunal = random.choice(TRIBUNALS)

    theme_number = random.randint(1, 9999)
    while theme_number in used_theme_numbers:
        theme_number = random.randint(1, 9999)
    used_theme_numbers.add(theme_number)

    return {
        "id": entry_id,
        "name": f"Tema {theme_number} {tribunal}",
        "tribunal": tribunal,
        "last_update": random_past_date(),
        "situation": random.choices(SITUATIONS, weights=SITUATION_WEIGHTS, k=1)[0],
        "url": TRIBUNAL_URLS[tribunal].format(theme_number),
        "description": random.choice(DESCRIPTIONS),
    }


def seed_redis(redis_client, count: int = 5):
    used_theme_numbers = set()

    for entry_id in range(1, count + 1):
        p = random_precedent(entry_id, used_theme_numbers)
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

    print(f"Redis seeded successfully with {count} entries")
