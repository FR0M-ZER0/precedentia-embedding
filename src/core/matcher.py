import math
import os
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Union

from sentence_transformers import CrossEncoder, SentenceTransformer

logger = logging.getLogger(__name__)

SPECIES_WEIGHTS: Dict[str, float] = {
    "Súmula Vinculante": 1.50,
    "Repercussão Geral": 1.40,
    "Ação Direta de Inconstitucionalidade (ADI)": 1.35,
    "Ação Declaratória de Constitucionalidade (ADC)": 1.35,
    "Arguição de Descumprimento de Preceito Fundamental (ADPF)": 1.30,
    "Recurso Especial Repetitivo": 1.20,
    "Incidente de Recurso de Revista Repetitivo": 1.20,
    "Incidente de Resolução de Demandas Repetitivas (IRDR)": 1.20,
    "Incidente de Assunção de Competência (IAC)": 1.15,
    "Súmula": 1.10,
    "Orientação Jurisprudencial": 1.05,
    "Súmula Regional": 1.05,
    "Resolução": 1.00,
    "Consulta": 1.00,
    "Acórdão em Recurso": 1.00,
    "Acórdão em Recurso Ordinário": 1.00,
    "Acórdão em Recurso Ordinário Militar": 1.00,
    "Enunciado": 1.00,
}

_QUERY_INSTRUCTION = (
    "Instruct: Recupere precedentes jurídicos brasileiros relevantes "
    "para os seguintes fatos processuais\nQuery: "
)

_RERANK_FACTS_WEIGHT = 0.60
_RERANK_REQUESTS_WEIGHT = 0.30
_RERANK_TYPE_WEIGHT = 0.10


class PrecedentMatcher:
    def __init__(
        self,
        qdrant_client,
        collection_name: str,
        model_name: str = "intfloat/multilingual-e5-large-instruct",
        reranker_name: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
    ):
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name
        self.encoder = SentenceTransformer(model_name)
        self.reranker = CrossEncoder(reranker_name)

        self.chunk_size = int(os.getenv("CHUNK_SIZE", 512))
        self.top_k = int(os.getenv("TOP_K", 100))
        self.final_k = int(os.getenv("FINAL_K", 20))
        self.score_threshold = float(os.getenv("SCORE_THRESHOLD", 0.1))

        self.rerank_facts_limit = int(os.getenv("RERANK_FACTS_LIMIT", 800))
        self.rerank_requests_limit = int(
            os.getenv("RERANK_REQUESTS_LIMIT", 400)
        )

        self.applicability_workers = int(os.getenv("APPLICABILITY_WORKERS", 5))

        self.applicability_url = os.getenv("APPLICABILITY_SERVICE_URL")
        self.applicability_timeout = int(
            os.getenv("APPLICABILITY_TIMEOUT", 30)
        )

    def chunk_text(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []
        if len(text) <= self.chunk_size:
            return [text]
        words = text.split()
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_length = 0

        for word in words:
            word_len = len(word) + 1
            if current_length + word_len <= self.chunk_size:
                current_chunk.append(word)
                current_length += word_len
            else:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_len
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        return chunks

    def _encode_query(self, text: str) -> List[float]:
        return self.encoder.encode(_QUERY_INSTRUCTION + text).tolist()

    def _encode_document(self, text: str) -> List[float]:
        return self.encoder.encode(text).tolist()

    def vector_search(self, query_vector: List[float]) -> List[Dict]:
        if not self.qdrant_client:
            logger.error(
                "Erro na busca vetorial: cliente Qdrant não inicializado"
            )
            return []
        try:
            if hasattr(self.qdrant_client, "search"):
                results = self.qdrant_client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=self.top_k,
                    with_payload=True,
                )
            elif hasattr(self.qdrant_client, "query_points"):
                query_response = self.qdrant_client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=self.top_k,
                    with_payload=True,
                )
                results = getattr(query_response, "points", query_response)
            else:
                logger.error(
                    "Erro na busca vetorial: método Qdrant incompatível"
                )
                return []

            return [
                {"id": r.id, "score": r.score, "payload": r.payload}
                for r in results
            ]
        except Exception as e:
            logger.error(f"Erro na busca vetorial: {e}")
            return []

    def _search_field(
            self, text: str, unique_results: Dict[int, Dict]
    ) -> None:
        full_query = text[:1000]
        query_vector = self._encode_query(full_query)
        for result in self.vector_search(query_vector):
            rid = result["id"]
            if rid not in unique_results or result["score"] > unique_results[rid]["score"]:
                unique_results[rid] = result

        for chunk in self.chunk_text(text):
            query_vector = self._encode_query(chunk)
            for result in self.vector_search(query_vector):
                rid = result["id"]
                if rid not in unique_results or result["score"] > unique_results[rid]["score"]:
                    unique_results[rid] = result

    def _build_rerank_query(
        self,
        petition_type: str,
        facts: str,
        requests: Union[str, List[str]],
    ) -> str:
        requests_text = (
            requests if isinstance(requests, str) else " ".join(requests)
        )

        facts_excerpt = facts[: self.rerank_facts_limit].strip()
        requests_excerpt = requests_text[: self.rerank_requests_limit].strip()

        parts = []
        if petition_type:
            parts.append(f"Tipo de ação: {petition_type}.")
        if facts_excerpt:
            parts.append(f"Fatos: {facts_excerpt}")
        if requests_excerpt:
            parts.append(f"Pedidos: {requests_excerpt}")

        return " ".join(parts)

    def rerank_results(
        self,
        rerank_query: str,
        results: List[Dict],
    ) -> List[Dict]:
        if not results:
            return results

        pairs = [
            [
                rerank_query,
                f"{r['payload'].get('name', '')}. {
                    r['payload'].get('description', '')
                }",
            ]
            for r in results
        ]
        scores = self.reranker.predict(pairs)

        for result, score in zip(results, scores):
            result["rerank_score"] = float(score)

        return results

    def compute_score(self, result: Dict) -> float:
        rerank = result.get("rerank_score", result["score"])
        return 1 / (1 + math.exp(-rerank))

    def compute_species_score(self, result: Dict) -> float:
        species = result["payload"].get("species", "")
        return SPECIES_WEIGHTS.get(species, 1.0)

    def _check_single_applicability(
        self,
        facts: str,
        petition_type: str,
        precedent: Dict,
    ) -> Dict:
        if not self.applicability_url:
            precedent.setdefault("applicability", "possible_applicability")
            precedent.setdefault("applicability_score", 0.5)
            precedent.setdefault("applicability_justification", None)
            return precedent

        try:
            response = requests.post(
                f"{self.applicability_url}/api/check-applicability",
                json={
                    "facts": facts,
                    "petition_type": petition_type,
                    # Aqui mantenho a estrutura de lista, mesmo que
                    # apenas um item esteja sendo mandado, isso para manter
                    # compatibilidade com a interface do precedentia-summary (
                    # ele espera uma lista de precedentes)
                    "precedents": [precedent],
                },
                timeout=self.applicability_timeout,
            )
            response.raise_for_status()
            enriched = response.json()["precedents"][0]
            precedent["applicability"] = enriched.get(
                "applicability", "possible_applicability"
            )
            precedent["applicability_score"] = enriched.get(
                "applicability_score", 0.5
            )
            precedent["applicability_justification"] = enriched.get(
                "applicability_justification"
            )
        except requests.Timeout:
            logger.warning(
                f"Timeout ao verificar aplicabilidade do precedente "
                f"'{precedent.get('name')}' — usando valor padrão."
            )
            precedent.setdefault("applicability", "possible_applicability")
            precedent.setdefault("applicability_score", 0.5)
            precedent.setdefault("applicability_justification", None)
        except Exception as e:
            logger.error(
                f"Erro ao verificar aplicabilidade do precedente "
                f"'{precedent.get('name')}': {e}"
            )
            precedent.setdefault("applicability", "possible_applicability")
            precedent.setdefault("applicability_score", 0.5)
            precedent.setdefault("applicability_justification", None)

        return precedent

    def _call_applicability_service(
        self,
        facts: str,
        petition_type: str,
        precedents: List[Dict],
    ) -> List[Dict]:
        if not self.applicability_url:
            logger.warning(
                "APPLICABILITY_SERVICE_URL não configurado — etapa ignorada."
            )
            return precedents
        try:
            response = requests.post(
                f"{self.applicability_url}/api/check-applicability",
                json={
                    "facts": facts,
                    "petition_type": petition_type,
                    "precedents": precedents,
                },
                timeout=self.applicability_timeout,
            )
            response.raise_for_status()
            return response.json()["precedents"]
        except requests.Timeout:
            logger.error(
                "Timeout ao verificar aplicabilidade — continuando sem filtro."
            )
        except requests.HTTPError as e:
            logger.error(f"Erro HTTP ao verificar aplicabilidade: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao verificar aplicabilidade: {e}")
        return precedents

    def _run_search_and_rerank(
        self,
        petition_type: str,
        tribunal: Optional[str],
        facts: str,
        requests: Union[str, List[str]],
    ) -> List[Dict]:
        unique_results: Dict[int, Dict] = {}

        if facts and facts.strip():
            self._search_field(facts, unique_results)

        requests_text = (
            requests
            if isinstance(requests, str)
            else " ".join(requests)
            if requests
            else ""
        )
        if requests_text and requests_text.strip():
            self._search_field(requests_text, unique_results)

        all_results = sorted(
            unique_results.values(),
            key=lambda x: x["score"],
            reverse=True,
        )[: self.top_k]

        for r in all_results:
            r["vector_score"] = r["score"]

        if all_results:
            rerank_query = self._build_rerank_query(
                petition_type, facts, requests or ""
            )
            if rerank_query.strip():
                all_results = self.rerank_results(rerank_query, all_results)

        for r in all_results:
            r["score"] = self.compute_score(r)

        return [r for r in all_results if r["score"] >= self.score_threshold]

    def _format_result(self, r: Dict) -> Dict:
        return {
            "id": r["id"],
            "name": r["payload"].get("name"),
            "tribunal": r["payload"].get("tribunal"),
            "species": r["payload"].get("species"),
            "situation": r["payload"].get("situation"),
            "description": r["payload"].get("description"),
            "question": r["payload"].get("question"),
            "summary": r.get("applicability_justification"),
            "url": r["payload"].get("url"),
            "last_update": r["payload"].get("last_update"),
            "score": round(r.get("vector_score", 0), 4),
            "score_species": r.get("score_species"),
            "applicability": r.get("applicability"),
            "applicability_justification": r.get(
                "applicability_justification"
            ),
        }

    def match_precedent(
        self,
        petition_type: str,
        tribunal: Optional[str],
        facts: str,
        requests: Union[str, List[str]],
    ) -> Dict[str, Any]:

        all_results = self._run_search_and_rerank(
            petition_type, tribunal, facts, requests
        )

        requests_text = (
            requests
            if isinstance(requests, str)
            else " ".join(requests)
            if requests
            else ""
        )

        if all_results and facts:
            precedents_payload = [
                {
                    "name": r["payload"].get("name"),
                    "species": r["payload"].get("species"),
                    "description": r["payload"].get("description"),
                    "summary": r["payload"].get("summary"),
                }
                for r in all_results
            ]

            enriched = self._call_applicability_service(
                facts, petition_type, precedents_payload
            )

            for r, enriched_r in zip(all_results, enriched):
                r["applicability"] = enriched_r.get(
                    "applicability", "possible_applicability"
                )
                r["applicability_score"] = enriched_r.get(
                    "applicability_score", 0.5
                )
                r["applicability_justification"] = enriched_r.get(
                    "applicability_justification"
                )

        applicability_priority = {
            "applicable": 3,
            "possible_applicability": 2,
            "low_applicability": 1,
        }

        all_results.sort(
            key=lambda x: (
                applicability_priority.get(x.get("applicability"), 0),
                x.get("vector_score", 0),
            ),
            reverse=True,
        )

        all_results = all_results[: self.final_k]

        facts_preview = facts[:200] + "..." if len(facts) > 200 else facts
        requests_preview = (
            requests_text[:200] + "..."
            if len(requests_text) > 200
            else requests_text
        )

        return {
            "query": {
                "type": petition_type,
                "tribunal": tribunal,
                "facts": facts_preview,
                "requests": requests_preview,
            },
            "results": [self._format_result(r) for r in all_results],
            "total_found": len(all_results),
        }

    def match_precedent_stream(
        self,
        petition_type: str,
        tribunal: Optional[str],
        facts: str,
        requests: Union[str, List[str]],
        emit: Callable[[str, Any], None],
    ) -> None:
        try:
            all_results = self._run_search_and_rerank(
                petition_type, tribunal, facts, requests
            )
        except Exception as e:
            logger.error(f"Erro na busca/rerank: {e}")
            emit("error", {"message": str(e)})
            return

        emit("search_complete", {"total": len(all_results)})

        all_results = all_results[: self.final_k]

        emit("rerank_complete", {"total": len(all_results)})

        if not all_results or not facts:
            emit("done", {"total_found": 0})
            return

        precedents_payload = [
            {
                "_index": idx,
                "name": r["payload"].get("name"),
                "species": r["payload"].get("species"),
                "description": r["payload"].get("description"),
                "summary": r["payload"].get("summary"),
                "_result": r,
            }
            for idx, r in enumerate(all_results)
        ]

        delivered = 0

        with ThreadPoolExecutor(
            max_workers=self.applicability_workers
        ) as executor:
            future_to_payload = {
                executor.submit(
                    self._check_single_applicability,
                    facts,
                    petition_type,
                    {k: v for k, v in p.items() if not k.startswith("_")},
                ): p
                for p in precedents_payload
            }

            for future in as_completed(future_to_payload):
                original_payload = future_to_payload[future]
                original_result = original_payload["_result"]
                original_index = original_payload["_index"]

                try:
                    enriched = future.result()
                except Exception as e:
                    logger.error(
                        f"Erro inesperado no future de aplicabilidade: {e}"
                    )
                    enriched = {
                        "applicability": "possible_applicability",
                        "applicability_score": 0.5,
                        "applicability_justification": None,
                    }

                original_result["applicability"] = enriched.get(
                    "applicability", "possible_applicability"
                )
                original_result["applicability_score"] = enriched.get(
                    "applicability_score", 0.5
                )
                original_result["applicability_justification"] = enriched.get(
                    "applicability_justification"
                )

                emit(
                    "precedent",
                    {
                        # Índice original para o front poder ordenar/inserir
                        # no lugar para manter a ordem do ranking
                        "index": original_index,
                        **self._format_result(original_result),
                    },
                )
                delivered += 1

        emit("done", {"total_found": delivered})
