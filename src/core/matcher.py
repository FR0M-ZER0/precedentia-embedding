import math
import os
from datetime import datetime
from typing import Any, Dict, List

from sentence_transformers import CrossEncoder, SentenceTransformer

SPECIES_WEIGHTS: Dict[str, float] = {
    # Vinculantes — uso obrigatório
    "Súmula Vinculante":                                         1.50,
    "Repercussão Geral":                                         1.40,
    "Ação Direta de Inconstitucionalidade (ADI)":                1.35,
    "Ação Declaratória de Constitucionalidade (ADC)":            1.35,
    "Arguição de Descumprimento de Preceito Fundamental (ADPF)": 1.30,
    # Forte persuasão — repetitivos e IAC
    "Recurso Especial Repetitivo":                               1.20,
    "Incidente de Recurso de Revista Repetitivo":                1.20,
    "Incidente de Resolução de Demandas Repetitivas (IRDR)":     1.20,
    "Incidente de Assunção de Competência (IAC)":                1.15,
    # Persuasivos
    "Súmula":                                                    1.10,
    "Orientação Jurisprudencial":                                1.05,
    "Súmula Regional":                                           1.05,
    # Base — sem peso extra
    "Resolução":                                                 1.00,
    "Consulta":                                                  1.00,
    "Acórdão em Recurso":                                        1.00,
    "Acórdão em Recurso Ordinário":                              1.00,
    "Acórdão em Recurso Ordinário Militar":                      1.00,
    "Enunciado":                                                 1.00,
}


def recency_factor(last_update_str: str, half_life_days: int = 730) -> float:
    """
    Fator de recência com decaimento logarítmico suave.
    - Atualizado hoje   → 1.0
    - Atualizado há ~2 anos → ~0.5
    """
    try:
        last_update = datetime.strptime(last_update_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return 1.0

    days_old = max((datetime.now() - last_update).days, 0)
    return 1.0 / (1.0 + math.log1p(days_old / half_life_days))


class PrecedentMatcher:
    def __init__(
        self,
        qdrant_client,
        collection_name: str,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name
        self.encoder = SentenceTransformer(model_name)
        self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

        self.top_k = int(os.getenv("TOP_K", 10))
        self.final_k = int(os.getenv("FINAL_K", 5))
        self.chunk_size = int(os.getenv("CHUNK_SIZE", 500))

    def prepare_query_text(self, facts: str, requests: str) -> str:
        parts = []
        if facts and facts.strip():
            parts.append(f"Fatos: {facts}")
        if requests and requests.strip():
            parts.append(f"Pedidos: {requests}")
        return " ".join(parts)

    def chunk_text(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]

        words = text.split()
        chunks, current_chunk, current_length = [], [], 0

        for word in words:
            if current_length + len(word) + 1 <= self.chunk_size:
                current_chunk.append(word)
                current_length += len(word) + 1
            else:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = len(word) + 1

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def vector_search(self, query_vector: List[float]) -> List[Dict]:
        if not self.qdrant_client:
            print("Erro na busca vetorial: cliente Qdrant não inicializado")
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
                print("Erro na busca vetorial: cliente Qdrant sem método de busca compatível")
                return []

            return [
                {"id": r.id, "score": r.score, "payload": r.payload}
                for r in results
            ]
        except Exception as e:
            print(f"Erro na busca vetorial: {e}")
            return []

    def rerank_results(self, query_text: str, results: List[Dict]) -> List[Dict]:
        if not results:
            return results

        pairs = [
            [query_text, f"{r['payload'].get('name', '')}. {r['payload'].get('description', '')}"]
            for r in results
        ]
        scores = self.reranker.predict(pairs)

        for result, score in zip(results, scores):
            result["rerank_score"] = float(score)

        return results

    def compute_final_score(self, result: Dict) -> float:
        rerank = result.get("rerank_score", result["score"])
        species = result["payload"].get("species", "")
        updated = result["payload"].get("last_update", "")

        rerank_normalized = 1 / (1 + math.exp(-rerank))

        w_species = SPECIES_WEIGHTS.get(species, 1.0)
        w_recency = recency_factor(updated)

        return rerank_normalized * w_species * w_recency

    def match_precedent(
        self, petition_type: str, tribunal: str, facts: str, requests: str
    ) -> Dict[str, Any]:

        query_text = self.prepare_query_text(facts, requests)
        chunks = self.chunk_text(query_text)

        unique_results: Dict[int, Dict] = {}
        for chunk in chunks:
            query_vector = self.encoder.encode(chunk).tolist()
            for result in self.vector_search(query_vector):
                rid = result["id"]
                if rid not in unique_results or result["score"] > unique_results[rid]["score"]:
                    unique_results[rid] = result

        all_results = sorted(unique_results.values(), key=lambda x: x["score"], reverse=True)
        all_results = all_results[: self.top_k]

        if all_results:
            all_results = self.rerank_results(query_text, all_results)

        for r in all_results:
            r["final_score"] = self.compute_final_score(r)

        all_results.sort(key=lambda x: x["final_score"], reverse=True)
        all_results = all_results[: self.final_k]

        return {
            "query": {
                "type": petition_type,
                "tribunal": tribunal,
                "facts": facts[:200] + "..." if len(facts) > 200 else facts,
                "requests": requests[:200] + "..." if len(requests) > 200 else requests,
            },
            "results": [
                {
                    "id": r["id"],
                    "name": r["payload"].get("name"),
                    "tribunal": r["payload"].get("tribunal"),
                    "species": r["payload"].get("species"),
                    "situation": r["payload"].get("situation"),
                    "description": r["payload"].get("description"),
                    "summary": r["payload"].get("summary"),
                    "url": r["payload"].get("url"),
                    "last_update": r["payload"].get("last_update"),
                    "score": round(r["final_score"], 4),
                }
                for r in all_results
            ],
            "total_found": len(all_results),
        }
