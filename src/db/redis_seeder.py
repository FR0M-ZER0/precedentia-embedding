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
    # Tributário - constitucionalidade
    "Discussão sobre a constitucionalidade de tributos estaduais instituídos sem observância dos princípios da legalidade e da anterioridade tributária, com análise dos limites do poder de tributar dos Estados-membros frente às normas constitucionais e à competência privativa da União para legislar sobre direito tributário geral.",
    "Análise da validade de leis estaduais que instituem alíquotas diferenciadas de ICMS em operações interestaduais, verificando possível violação ao princípio da não discriminação tributária e ao pacto federativo, com repercussão direta sobre a guerra fiscal entre os entes federativos.",
    # Responsabilidade civil bancária
    "Responsabilidade civil de instituições financeiras em contratos bancários que contêm cláusulas abusivas, com enfoque na aplicação do Código de Defesa do Consumidor às relações de crédito, revisão de encargos moratórios excessivos e dever de transparência na oferta de produtos e serviços financeiros.",
    "Discussão acerca do dever de indenizar dos bancos em casos de fraudes eletrônicas e clonagem de cartões, analisando a teoria do risco do negócio, a responsabilidade objetiva das instituições financeiras e os limites da excludente de responsabilidade por culpa exclusiva do consumidor.",
    # Previdenciário
    "Revisão dos critérios de concessão de benefícios previdenciários, em especial o auxílio-doença e a aposentadoria por invalidez, com análise da suficiência da prova pericial, do conceito de incapacidade laborativa e da vinculação do INSS ao laudo médico produzido na via administrativa.",
    "Controvérsia sobre o direito à revisão da renda mensal inicial de benefícios previdenciários concedidos com base em salários de contribuição anteriores ao Plano Real, examinando a aplicação do artigo 29 da Lei nº 8.213/91 e a decadência do direito à revisão prevista no artigo 103 do mesmo diploma.",
    # Ambiental
    "Validade de normas ambientais estaduais que impõem restrições ao uso de propriedade rural além dos limites estabelecidos pelo Código Florestal Federal, com análise da competência legislativa concorrente em matéria ambiental, do princípio da vedação ao retrocesso ambiental e dos direitos dos proprietários.",
    "Responsabilidade solidária de empresas pelo passivo ambiental decorrente de danos causados ao meio ambiente em áreas contaminadas, discutindo os critérios de imputação, a desconsideração da personalidade jurídica em grupos econômicos e a extensão da obrigação de recuperação ambiental ao adquirente do imóvel.",
    # Execução fiscal
    "Aplicação do instituto da prescrição intercorrente nas execuções fiscais de créditos tributários federais, estaduais e municipais, com definição do termo inicial da contagem do prazo, das hipóteses de suspensão e interrupção e dos efeitos da inércia da Fazenda Pública na movimentação do feito.",
    "Discussão sobre os limites da responsabilidade de sócios e administradores pelo redirecionamento da execução fiscal em casos de dissolução irregular de sociedade, com análise da Súmula 435 do STJ, do ônus da prova e das causas excludentes da responsabilidade tributária de terceiros.",
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
