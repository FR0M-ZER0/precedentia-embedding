# PrecedentIA - Embedding

Serviço do sistema **PrecedentIA**, desenvolvido em Python, responsável por transformar precedentes jurídicos e petições iniciais em vetores semânticos, além de realizar o reranking dos resultados utilizando Cross Encoder.

## 🚀 Tecnologias Utilizadas

O projeto utiliza as seguintes tecnologias e bibliotecas:

- **Python** - Linguagem principal do serviço
- **Sentence Transformers** - Geração de embeddings semânticos a partir de textos jurídicos
- **Cross Encoder** - Reranking dos resultados de busca por relevância semântica
- **Qdrant Client** - Integração com o banco de dados vetorial Qdrant para armazenamento e busca de embeddings
- **Python-dotenv** - Gerenciamento de variáveis de ambiente via arquivo `.env`
- **Pytest** - Framework de testes para testes unitários e de integração

## ⚙️ Rodando o Projeto

### 1️⃣ Verifique o ambiente Python

Execute o comando abaixo para garantir que está utilizando a versão correta do Python (3.12+):

```bash
python --version
```

### 2️⃣ Crie e ative o ambiente virtual

```bash
python -m venv .venv       # Ou python3 no linux
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

### 3️⃣ Instale os pacotes Node.js e ative os hooks de commit

Instale os pacotes necessários para validação de commits:

```bash
npm i
```

Em seguida, ative os hooks do Husky:

```bash
npm run prepare
```

> O comando `npm run prepare` ativa o **Husky**, responsável por executar validações automáticas antes de cada commit.

> **Atenção:** Sempre ative o ambiente virtual do python antes de commitar.

### 4️⃣ Instale as dependências Python

```bash
pip install -r requirements.txt
```

### 5️⃣ Configure as variáveis de ambiente

Copie o arquivo de exemplo e preencha com os valores adequados:

```bash
cp .env.example .env
```

### 6️⃣ Execute a aplicação

```bash
python -m src.main
# ou
python src/main.py
```

## 🧪 Rodando os testes

Para executar a suite de testes do projeto:

```bash
pytest
```

Para rodar com cobertura de código:

```bash
pytest --cov=app
```

## Saiba mais

Para verificar as padronizações usadas neste projeto, bem como demais documentações, visite o nosso [repositório principal](https://github.com/FR0M-ZER0/PrecedentIA)