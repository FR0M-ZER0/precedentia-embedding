from datetime import datetime, timedelta
import random

# ---------------------------------------------------------------------------
# Tribunais Superiores
# ---------------------------------------------------------------------------
TRIBUNAIS_SUPERIORES = ["STF", "STJ", "TST", "TSE", "STM"]

# ---------------------------------------------------------------------------
# Tribunais Regionais Federais
# ---------------------------------------------------------------------------
TRIBUNAIS_REGIONAIS_FEDERAIS = ["TRF1", "TRF2", "TRF3", "TRF4", "TRF5"]

# ---------------------------------------------------------------------------
# Tribunais de Justiça dos Estados + DF
# ---------------------------------------------------------------------------
TRIBUNAIS_DE_JUSTICA = [
    "TJAC",
    "TJAL",
    "TJAP",
    "TJAM",
    "TJBA",
    "TJCE",
    "TJDFT",
    "TJES",
    "TJGO",
    "TJMA",
    "TJMT",
    "TJMS",
    "TJMG",
    "TJPA",
    "TJPB",
    "TJPR",
    "TJPE",
    "TJPI",
    "TJRJ",
    "TJRN",
    "TJRS",
    "TJRO",
    "TJRR",
    "TJSC",
    "TJSP",
    "TJSE",
    "TJTO",
]

# ---------------------------------------------------------------------------
# Tribunais Regionais do Trabalho
# ---------------------------------------------------------------------------
TRIBUNAIS_REGIONAIS_TRABALHO = [f"TRT{i}" for i in range(1, 25)]

# ---------------------------------------------------------------------------
# Tribunais Regionais Eleitorais
# ---------------------------------------------------------------------------
TRIBUNAIS_REGIONAIS_ELEITORAIS = [
    "TREAC",
    "TREAL",
    "TREAP",
    "TREAM",
    "TREBA",
    "TRECE",
    "TREDF",
    "TREES",
    "TREGO",
    "TREMA",
    "TREMT",
    "TREMS",
    "TREMG",
    "TREPA",
    "TREPB",
    "TREPR",
    "TREPE",
    "TREPI",
    "TRERJ",
    "TRERN",
    "TRERS",
    "TRERO",
    "TRERR",
    "TRESC",
    "TRESP",
    "TRESE",
    "TRETO",
]

# ---------------------------------------------------------------------------
# Tribunais Militares Estaduais
# ---------------------------------------------------------------------------
TRIBUNAIS_MILITARES = ["TJMMG", "TJMRS", "TJMSP"]

# ---------------------------------------------------------------------------
# Consolidação de todos os tribunais
# ---------------------------------------------------------------------------
TRIBUNALS = (
    TRIBUNAIS_SUPERIORES
    + TRIBUNAIS_REGIONAIS_FEDERAIS
    + TRIBUNAIS_DE_JUSTICA
    + TRIBUNAIS_REGIONAIS_TRABALHO
    + TRIBUNAIS_REGIONAIS_ELEITORAIS
    + TRIBUNAIS_MILITARES
)

# ---------------------------------------------------------------------------
# URLs base por tribunal
# ---------------------------------------------------------------------------
_URL_BASES = {
    "STF": "https://portal.stf.jus.br/jurisprudenciaRepercussao/tema.asp?num={}",
    "STJ": "https://processo.stj.jus.br/repetitivos/temas_repetitivos/pesquisa.jsp?tema={}",
    "TST": "https://jurisprudencia.tst.jus.br/tema/{}",
    "TSE": "https://www.tse.jus.br/jurisprudencia/tema/{}",
    "STM": "https://www.stm.jus.br/jurisprudencia/tema/{}",
}
for _n in range(1, 6):
    _URL_BASES[f"TRF{_n}"] = f"https://www.trf{_n}.jus.br/jurisprudencia/tema/{{}}"
for _uf in [
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DFT",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
]:
    _URL_BASES[f"TJ{_uf}"] = (
        f"https://www.tj{_uf.lower()}.jus.br/jurisprudencia/tema/{{}}"
    )
for _n in range(1, 25):
    _URL_BASES[f"TRT{_n}"] = f"https://www.trt{_n}.jus.br/jurisprudencia/tema/{{}}"
for _uf in [
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
]:
    _URL_BASES[f"TRE{_uf}"] = (
        f"https://www.tre-{_uf.lower()}.jus.br/jurisprudencia/tema/{{}}"
    )
_URL_BASES["TJMMG"] = "https://www.tjmmg.jus.br/jurisprudencia/tema/{}"
_URL_BASES["TJMRS"] = "https://www.tjmrs.jus.br/jurisprudencia/tema/{}"
_URL_BASES["TJMSP"] = "https://www.tjmsp.jus.br/jurisprudencia/tema/{}"

TRIBUNAL_URLS: dict[str, str] = _URL_BASES

# ---------------------------------------------------------------------------
# Espécies de precedente com respectivo tribunal-âncora
# ---------------------------------------------------------------------------
ESPECIES_POR_TRIBUNAL: dict[str, list[str]] = {
    # STF: controle concentrado + repercussão geral
    "STF": [
        "Repercussão Geral",
        "Ação Direta de Inconstitucionalidade (ADI)",
        "Ação Declaratória de Constitucionalidade (ADC)",
        "Arguição de Descumprimento de Preceito Fundamental (ADPF)",
        "Súmula Vinculante",
    ],
    # STJ: recursos repetitivos + súmulas
    "STJ": [
        "Recurso Especial Repetitivo",
        "Incidente de Assunção de Competência (IAC)",
        "Súmula",
    ],
    # TST: recursos repetitivos trabalhistas + súmulas
    "TST": [
        "Incidente de Recurso de Revista Repetitivo",
        "Súmula",
        "Orientação Jurisprudencial",
    ],
    # TSE: resolução + consulta
    "TSE": [
        "Resolução",
        "Consulta",
        "Súmula",
    ],
    # STM: acórdão em recurso ordinário
    "STM": [
        "Acórdão em Recurso Ordinário",
        "Súmula",
    ],
}
# TRFs
for _n in range(1, 6):
    ESPECIES_POR_TRIBUNAL[f"TRF{_n}"] = [
        "Incidente de Resolução de Demandas Repetitivas (IRDR)",
        "Incidente de Assunção de Competência (IAC)",
        "Súmula",
    ]
# TJs
for _uf in [
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DFT",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
]:
    ESPECIES_POR_TRIBUNAL[f"TJ{_uf}"] = [
        "Incidente de Resolução de Demandas Repetitivas (IRDR)",
        "Incidente de Assunção de Competência (IAC)",
        "Súmula",
        "Enunciado",
    ]
# TRTs
for _n in range(1, 25):
    ESPECIES_POR_TRIBUNAL[f"TRT{_n}"] = [
        "Incidente de Recurso de Revista Repetitivo",
        "Orientação Jurisprudencial",
        "Súmula Regional",
    ]
# TREs
for _uf in [
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
]:
    ESPECIES_POR_TRIBUNAL[f"TRE{_uf}"] = [
        "Resolução",
        "Consulta",
        "Acórdão em Recurso",
    ]
# TJMs
ESPECIES_POR_TRIBUNAL["TJMMG"] = ["Acórdão em Recurso Ordinário Militar", "Súmula"]
ESPECIES_POR_TRIBUNAL["TJMRS"] = ["Acórdão em Recurso Ordinário Militar", "Súmula"]
ESPECIES_POR_TRIBUNAL["TJMSP"] = ["Acórdão em Recurso Ordinário Militar", "Súmula"]

# Fallback para tribunais não mapeados
_ESPECIES_FALLBACK = [
    "Incidente de Resolução de Demandas Repetitivas (IRDR)",
    "Súmula",
    "Acórdão em Recurso",
]

# ---------------------------------------------------------------------------
# Descrições por área temática
# ---------------------------------------------------------------------------
DESCRIPTIONS = [
    # Tributário — constitucionalidade
    "Discussão sobre a constitucionalidade de tributos estaduais instituídos sem observância dos "
    "princípios da legalidade e da anterioridade tributária, com análise dos limites do poder de "
    "tributar dos Estados-membros frente às normas constitucionais e à competência privativa da "
    "União para legislar sobre direito tributário geral.",
    "Análise da validade de leis estaduais que instituem alíquotas diferenciadas de ICMS em "
    "operações interestaduais, verificando possível violação ao princípio da não discriminação "
    "tributária e ao pacto federativo, com repercussão direta sobre a guerra fiscal entre os "
    "entes federativos.",
    # Responsabilidade civil bancária
    "Responsabilidade civil de instituições financeiras em contratos bancários que contêm "
    "cláusulas abusivas, com enfoque na aplicação do Código de Defesa do Consumidor às relações "
    "de crédito, revisão de encargos moratórios excessivos e dever de transparência na oferta de "
    "produtos e serviços financeiros.",
    "Discussão acerca do dever de indenizar dos bancos em casos de fraudes eletrônicas e "
    "clonagem de cartões, analisando a teoria do risco do negócio, a responsabilidade objetiva "
    "das instituições financeiras e os limites da excludente de responsabilidade por culpa "
    "exclusiva do consumidor.",
    # Previdenciário
    "Revisão dos critérios de concessão de benefícios previdenciários, em especial o "
    "auxílio-doença e a aposentadoria por invalidez, com análise da suficiência da prova "
    "pericial, do conceito de incapacidade laborativa e da vinculação do INSS ao laudo médico "
    "produzido na via administrativa.",
    "Controvérsia sobre o direito à revisão da renda mensal inicial de benefícios previdenciários "
    "concedidos com base em salários de contribuição anteriores ao Plano Real, examinando a "
    "aplicação do artigo 29 da Lei nº 8.213/91 e a decadência do direito à revisão prevista no "
    "artigo 103 do mesmo diploma.",
    # Ambiental
    "Validade de normas ambientais estaduais que impõem restrições ao uso de propriedade rural "
    "além dos limites estabelecidos pelo Código Florestal Federal, com análise da competência "
    "legislativa concorrente em matéria ambiental, do princípio da vedação ao retrocesso "
    "ambiental e dos direitos dos proprietários.",
    "Responsabilidade solidária de empresas pelo passivo ambiental decorrente de danos causados "
    "ao meio ambiente em áreas contaminadas, discutindo os critérios de imputação, a "
    "desconsideração da personalidade jurídica em grupos econômicos e a extensão da obrigação de "
    "recuperação ambiental ao adquirente do imóvel.",
    # Execução fiscal
    "Aplicação do instituto da prescrição intercorrente nas execuções fiscais de créditos "
    "tributários federais, estaduais e municipais, com definição do termo inicial da contagem do "
    "prazo, das hipóteses de suspensão e interrupção e dos efeitos da inércia da Fazenda Pública "
    "na movimentação do feito.",
    "Discussão sobre os limites da responsabilidade de sócios e administradores pelo "
    "redirecionamento da execução fiscal em casos de dissolução irregular de sociedade, com "
    "análise da Súmula 435 do STJ, do ônus da prova e das causas excludentes da "
    "responsabilidade tributária de terceiros.",
    # Trabalhista
    "Controvérsia sobre o reconhecimento de vínculo empregatício em relações de trabalho "
    "mediadas por plataformas digitais, com análise dos elementos caracterizadores da relação de "
    "emprego — subordinação, pessoalidade, habitualidade e onerosidade — frente ao modelo de "
    "trabalho por demanda (gig economy).",
    "Discussão sobre os limites do poder diretivo do empregador na fixação de metas e controle "
    "de produtividade, analisando a licitude de cláusulas de não concorrência no contrato de "
    "trabalho e os critérios para o pagamento de indenização compensatória ao empregado.",
    # Direito do consumidor
    "Abusividade de cláusulas contratuais em contratos de adesão de planos de saúde que limitam "
    "o tempo de internação e excluem cobertura para procedimentos considerados experimentais, com "
    "base no Código de Defesa do Consumidor e nas normas da Agência Nacional de Saúde "
    "Suplementar.",
    "Responsabilidade civil de fornecedores de produtos e serviços por danos causados a "
    "consumidores em razão de defeitos de concepção e fabricação, com análise da teoria do risco "
    "do desenvolvimento como excludente de responsabilidade e os critérios de reparação integral "
    "do dano.",
    # Direito eleitoral
    "Análise dos requisitos constitucionais e legais para a cassação de mandatos eletivos em "
    "razão de abuso de poder econômico e captação ilícita de sufrágio, com discussão sobre o "
    "grau de influência necessário para a configuração das infrações e o prazo decadencial para "
    "ajuizamento da Ação de Investigação Judicial Eleitoral.",
    # Direito penal / processo penal
    "Discussão sobre a aplicação do princípio da insignificância aos crimes contra a ordem "
    "tributária, analisando os critérios objetivos fixados pelo STF — mínima ofensividade, "
    "ausência de periculosidade, reduzido grau de reprovabilidade e inexpressividade da lesão "
    "jurídica — e os limites de valor do crédito tributário.",
    "Controvérsia acerca da legalidade de provas obtidas mediante compartilhamento de dados "
    "fiscais e bancários entre o Fisco e o Ministério Público sem prévia autorização judicial, "
    "com análise do sigilo bancário, do direito à privacidade e das garantias do processo penal "
    "acusatório.",
    # Administrativo
    "Limites do controle judicial sobre atos de improbidade administrativa praticados por agentes "
    "públicos, com análise dos elementos subjetivos do tipo, da proporcionalidade das sanções "
    "previstas na Lei nº 8.429/92, alterada pela Lei nº 14.230/21, e do prazo prescricional.",
    "Discussão sobre o dever de indenizar do Estado em casos de responsabilidade civil objetiva "
    "por omissão, analisando a teoria do risco administrativo, o nexo de causalidade entre a "
    "inação do Poder Público e o dano sofrido pelo particular e os limites da reserva do "
    "possível.",
    # Família e sucessões
    "Reconhecimento e dissolução de uniões estáveis simultâneas ou concomitantes ao casamento, "
    "com análise das consequências jurídicas para fins de partilha de bens, alimentos e direitos "
    "sucessórios, à luz do princípio da boa-fé objetiva e da vedação ao enriquecimento sem "
    "causa.",
]

# ---------------------------------------------------------------------------
# Resumos gerados por IA
# ---------------------------------------------------------------------------
AI_SUMMARIES = [
    # 0 — Tributário constitucionalidade
    "Este precedente trata da constitucionalidade de tributos estaduais criados fora dos "
    "parâmetros fixados pela Constituição Federal. Classificado como precedente de caráter "
    "tributário-constitucional, é utilizado por advogados e procuradores para questionar "
    "exigências fiscais que desrespeitem a legalidade estrita ou a anterioridade, servindo "
    "como paradigma em ações anulatórias e mandados de segurança preventivos.",
    # 1 — ICMS interestadual
    "Precedente que consolida o entendimento sobre alíquotas diferenciadas de ICMS entre "
    "estados, com natureza tributário-federativa. É amplamente invocado em processos que "
    "discutem a chamada guerra fiscal, sendo referência obrigatória para contribuintes que "
    "buscam restituição de valores recolhidos a maior e para estados que defendem a validade "
    "de seus benefícios fiscais.",
    # 2 — Responsabilidade bancária CDC
    "De natureza consumerista-bancária, este precedente delimita a responsabilidade das "
    "instituições financeiras em contratos de crédito com cláusulas abusivas. Aplica-se em "
    "ações revisionais de contratos, sendo utilizado por consumidores para pleitear a "
    "readequação de encargos e por juízes de primeiro grau como fundamento para sentenças "
    "que afastam cobranças ilegais.",
    # 3 — Fraude eletrônica bancária
    "Precedente de responsabilidade civil objetiva no setor bancário digital, enquadrado na "
    "espécie consumerista. Define que bancos respondem pelos riscos inerentes à sua atividade "
    "frente a fraudes eletrônicas, sendo citado em ações indenizatórias por clonagem de "
    "cartão e phishing para afastar a tese de culpa exclusiva do consumidor.",
    # 4 — Concessão de benefício previdenciário
    "Precedente de direito previdenciário que orienta a concessão de auxílio-doença e "
    "aposentadoria por invalidez. Utilizado em recursos contra o INSS para demonstrar que a "
    "autarquia não pode negar benefício contrariando laudo pericial favorável ao segurado, "
    "servindo de base tanto em ações ordinárias quanto em juizados especiais federais.",
    # 5 — Revisão do benefício pré-Plano Real
    "Precedente previdenciário-revisional que trata do recálculo de benefícios com base em "
    "contribuições anteriores à estabilização monetária. É referenciado em ações de revisão "
    "do ato de concessão para discutir o índice de correção aplicável aos salários de "
    "contribuição e para questionar a decadência decenal que extingue o direito à revisão.",
    # 6 — Norma ambiental estadual x Código Florestal
    "Precedente de direito ambiental-federativo que examina o alcance da competência "
    "legislativa concorrente dos estados em matéria de proteção florestal. Invocado em ações "
    "civis públicas e mandados de segurança por proprietários rurais que contestam restrições "
    "mais severas que as do Código Florestal, bem como pelo Ministério Público Ambiental para "
    "defender normas protetivas locais.",
    # 7 — Passivo ambiental solidário
    "Precedente de responsabilidade ambiental solidária em grupos econômicos, com natureza "
    "civil-ambiental. Utilizado em ações de recuperação de áreas degradadas para imputar "
    "obrigações ao adquirente de imóvel contaminado e para fundamentar a desconsideração da "
    "personalidade jurídica de empresas que se dissolvem para fugir do passivo ambiental.",
    # 8 — Prescrição intercorrente na execução fiscal
    "Precedente de direito processual tributário que regulamenta a prescrição intercorrente "
    "em execuções fiscais paralisadas. É frequentemente citado por devedores para obter a "
    "extinção do feito e pela Fazenda Pública para sustentar a ausência de sua inércia, sendo "
    "essencial na prática de escritórios que atuam em recuperação de crédito público e privado.",
    # 9 — Redirecionamento de execução fiscal para sócios
    "Precedente tributário-societário que define as condições para o redirecionamento da "
    "cobrança fiscal ao patrimônio pessoal de sócios e administradores. Aplicado em embargos "
    "à execução e exceções de pré-executividade para demonstrar que a mera inadimplência não "
    "autoriza o redirecionamento, exigindo prova de dissolução irregular ou ato ilícito.",
    # 10 — Vínculo empregatício em plataformas digitais
    "Precedente trabalhista de vanguarda que discute a caracterização da relação de emprego "
    "nos modelos de trabalho por plataformas digitais. Citado em reclamações trabalhistas "
    "movidas por motoristas e entregadores contra empresas de tecnologia, serve de paradigma "
    "para o reconhecimento retroativo de direitos como FGTS, férias e 13º salário.",
    # 11 — Cláusula de não concorrência
    "Precedente trabalhista-contratual que traça os limites do poder diretivo empresarial "
    "quanto à imposição de metas e restrições pós-contratuais. Utilizado por trabalhadores "
    "que se sentem lesados por cláusulas de não concorrência excessivamente amplas e por "
    "empresas que buscam proteger segredos industriais, orientando a fixação de indenizações "
    "proporcionais ao período de restrição.",
    # 12 — Plano de saúde — limitação de cobertura
    "Precedente consumerista-securitário que combate cláusulas restritivas de cobertura em "
    "planos de saúde. Amplamente utilizado em ações de obrigação de fazer para compelir "
    "operadoras a custear internações prolongadas e procedimentos modernos, tendo como "
    "fundamento a função social do contrato e as resoluções normativas da ANS.",
    # 13 — Responsabilidade pelo defeito do produto
    "Precedente consumerista de responsabilidade pelo fato do produto, que analisa a "
    "excludente do risco do desenvolvimento. Serve de referência em ações indenizatórias "
    "coletivas e individuais contra fabricantes de produtos defeituosos, orientando o "
    "judiciário sobre os requisitos para afastar a responsabilidade objetiva e sobre a "
    "amplitude da reparação integral.",
    # 14 — Cassação de mandato eleitoral
    "Precedente de direito eleitoral que define os critérios para cassação de mandato por "
    "abuso de poder econômico. Utilizado pela Justiça Eleitoral na apreciação de AIJEs e "
    "RIJEs, serve de parâmetro para quantificar o grau de influência exigido e para delimitar "
    "o prazo decadencial das ações, sendo essencial na advocacia eleitoral de alto risco.",
    # 15 — Insignificância em crimes tributários
    "Precedente penal-tributário que regulamenta a aplicação do princípio da insignificância "
    "a débitos fiscais de pequeno valor. Invocado em habeas corpus e recursos em sentido "
    "estrito para obter o trancamento de ação penal ou absolvição, consolidando os patamares "
    "de valor do crédito fiscal abaixo dos quais a conduta é atípica pela ausência de "
    "relevância jurídica.",
    # 16 — Compartilhamento de dados fiscais sem autorização judicial
    "Precedente de processo penal-constitucional que examina a licitude da prova obtida por "
    "compartilhamento de dados bancários e fiscais sem ordem judicial. Citado na defesa de "
    "réus em ações penais tributárias para nulificar provas ilícitas e pelo Ministério "
    "Público para sustentar a constitucionalidade do fluxo de informações entre órgãos de "
    "persecução.",
    # 17 — Improbidade administrativa
    "Precedente administrativo-sancionador que delimita os elementos subjetivos da "
    "improbidade administrativa após a reforma legislativa de 2021. É imprescindível em "
    "ações civis públicas por ato de improbidade para demonstrar o dolo específico exigido "
    "e na dosimetria das sanções, orientando tanto o Ministério Público quanto os "
    "advogados de defesa de agentes públicos.",
    # 18 — Responsabilidade civil do Estado por omissão
    "Precedente de direito administrativo sobre responsabilidade civil extracontratual do "
    "Estado por omissão genérica e específica. Utilizado em ações indenizatórias contra o "
    "Poder Público por danos decorrentes da falta de prestação de serviços essenciais, "
    "analisando a reserva do possível como limite legítimo à condenação do Estado.",
    # 19 — União estável simultânea
    "Precedente de direito de família e sucessões que trata do reconhecimento jurídico de "
    "uniões estáveis concomitantes ao casamento. Referência em inventários e partilhas "
    "litigiosas para definir os direitos da companheira sobre bens do de cujus, "
    "equilibrando a tutela da confiança legítima com a vedação ao enriquecimento sem "
    "causa e ao bis in idem sucessório.",
]

assert len(AI_SUMMARIES) == len(DESCRIPTIONS), (
    "AI_SUMMARIES e DESCRIPTIONS devem ter o mesmo tamanho."
)

SITUATIONS = ["Ativo", "Suspenso", "Finalizado"]
SITUATION_WEIGHTS = [0.6, 0.2, 0.2]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def random_past_date() -> str:
    days_ago = random.randint(1, 730)
    random_date = datetime.now() - timedelta(days=days_ago)
    return random_date.strftime("%Y-%m-%d %H:%M:%S")


def get_especie(tribunal: str) -> str:
    especies = ESPECIES_POR_TRIBUNAL.get(tribunal, _ESPECIES_FALLBACK)
    return random.choice(especies)


def get_url(tribunal: str, theme_number: int) -> str:
    template = TRIBUNAL_URLS.get(
        tribunal, "https://www.jusbrasil.com.br/jurisprudencia/{}"
    )
    return template.format(theme_number)


def random_precedent(entry_id: int, used_theme_numbers: set) -> dict:
    tribunal = random.choice(TRIBUNALS)

    theme_number = random.randint(1, 9999)
    while theme_number in used_theme_numbers:
        theme_number = random.randint(1, 9999)
    used_theme_numbers.add(theme_number)

    pair_index = random.randint(0, len(DESCRIPTIONS) - 1)

    return {
        "id": entry_id,
        "name": f"Tema {theme_number} {tribunal}",
        "tribunal": tribunal,
        "species": get_especie(tribunal),
        "last_update": random_past_date(),
        "situation": random.choices(SITUATIONS, weights=SITUATION_WEIGHTS, k=1)[0],
        "url": get_url(tribunal, theme_number),
        "description": DESCRIPTIONS[pair_index],
        "summary": AI_SUMMARIES[pair_index],
    }


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------


def seed_redis(redis_client, count: int = 5) -> None:
    used_theme_numbers: set[int] = set()

    for entry_id in range(1, count + 1):
        p = random_precedent(entry_id, used_theme_numbers)
        key = f"precedent:{p['id']}"

        redis_client.hset(
            key,
            mapping={
                "name": p["name"],
                "tribunal": p["tribunal"],
                "species": p["species"],
                "last_update": p["last_update"],
                "situation": p["situation"],
                "url": p["url"],
                "description": p["description"],
                "summary": p["summary"],
            },
        )

    print(f"Redis seeded successfully with {count} entries")
