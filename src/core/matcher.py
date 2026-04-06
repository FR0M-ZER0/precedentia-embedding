import math
import os
from typing import Any, Dict, List

from sentence_transformers import CrossEncoder, SentenceTransformer

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
        self.chunk_size = int(os.getenv("CHUNK_SIZE", 150))
        self.score_threshold = float(os.getenv("SCORE_THRESHOLD", 0.1))

    def chunk_text(self, text: str) -> List[str]:
        if not text or not text.strip():
            return []

        if len(text) <= self.chunk_size:
            return [text]

        words = text.split()
        chunks, current_chunk, current_length = [], [], 0

        for word in words:
            if current_length + len(word) + 1 <= self.chunk_size:
                current_chunk.append(word)
                current_length += len(word) + 1
            else:
                if current_chunk:
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
                print(
                    "Erro na busca vetorial: cliente Qdrant sem método de busca compatível"
                )
                return []

            return [
                {"id": r.id, "score": r.score, "payload": r.payload} for r in results
            ]
        except Exception as e:
            print(f"Erro na busca vetorial: {e}")
            return []

    def _search_field(self, text: str, unique_results: Dict[int, Dict]) -> None:
        for chunk in self.chunk_text(text):
            query_vector = self.encoder.encode(chunk).tolist()
            for result in self.vector_search(query_vector):
                rid = result["id"]
                if (
                    rid not in unique_results
                    or result["score"] > unique_results[rid]["score"]
                ):
                    unique_results[rid] = result

    def rerank_results(self, query_text: str, results: List[Dict]) -> List[Dict]:
        if not results:
            return results

        pairs = [
            [
                query_text,
                f"{r['payload'].get('name', '')}. {r['payload'].get('description', '')}",
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

    def match_precedent(
        self, petition_type: str, tribunal: str, facts: str, requests: str
    ) -> Dict[str, Any]:

        unique_results: Dict[int, Dict] = {}

        if facts and facts.strip():
            self._search_field(facts, unique_results)

        all_results = sorted(
            unique_results.values(), key=lambda x: x["score"], reverse=True
        )
        all_results = all_results[: self.top_k]

        rerank_query = facts[:500] if facts else ""
        if all_results and rerank_query:
            all_results = self.rerank_results(rerank_query, all_results)

        for r in all_results:
            r["score"] = self.compute_score(r)
            r["score_species"] = self.compute_species_score(r)

        all_results.sort(
            key=lambda x: (x["score"], x["score_species"]),
            reverse=True
        )

        all_results = [
            r for r in all_results if r["score"] >= self.score_threshold
        ]

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
                    "score": round(r["score"], 4),
                    "score_species": r["score_species"],
                }
                for r in all_results
            ],
            "total_found": len(all_results),
        }
