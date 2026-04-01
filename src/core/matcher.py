import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer, CrossEncoder
import os

class PrecedentMatcher:
    def __init__(self, qdrant_client, collection_name: str, model_name: str = "all-MiniLM-L6-v2"):
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name
        self.encoder = SentenceTransformer(model_name)
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        self.top_k = int(os.getenv('TOP_K', 10))
        self.final_k = int(os.getenv('FINAL_K', 5))
        self.chunk_size = int(os.getenv('CHUNK_SIZE', 500))
        
    def prepare_query_text(self, facts: str, requests: str) -> str:
        """Prepara o texto da query combinando fatos e pedidos"""
        query_parts = []
        
        if facts and facts.strip():
            query_parts.append(f"Fatos: {facts}")
        if requests and requests.strip():
            query_parts.append(f"Pedidos: {requests}")
            
        return " ".join(query_parts)
    
    def chunk_text(self, text: str) -> List[str]:
        """Divide texto grande em chunks menores"""
        if len(text) <= self.chunk_size:
            return [text]
        
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
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
    
    def filter_by_tribunal(self, results: List[Dict], tribunal: str) -> List[Dict]:
        """Filtra resultados pelo tribunal"""
        if not tribunal:
            return results
            
        filtered = []
        for result in results:
            if result.get('payload', {}).get('tribunal') == tribunal:
                filtered.append(result)
        
        return filtered
    
    def vector_search(self, query_vector: List[float]) -> List[Dict]:
        """Busca vetorial no Qdrant"""
        if not self.qdrant_client:
            print("Erro na busca vetorial: cliente Qdrant não inicializado")
            return []

        try:
            if hasattr(self.qdrant_client, "search"):
                results = self.qdrant_client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=self.top_k,
                    with_payload=True
                )
            elif hasattr(self.qdrant_client, "query_points"):
                query_response = self.qdrant_client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=self.top_k,
                    with_payload=True
                )
                results = getattr(query_response, "points", query_response)
            else:
                print("Erro na busca vetorial: cliente Qdrant sem método de busca compatível")
                return []
            
            return [
                {
                    'id': result.id,
                    'score': result.score,
                    'payload': result.payload
                }
                for result in results
            ]
        except Exception as e:
            print(f"Erro na busca vetorial: {e}")
            return []
    
    def rerank_results(self, query_text: str, results: List[Dict]) -> List[Dict]:
        """Reordena resultados usando CrossEncoder"""
        if not results:
            return results
        
        pairs = []
        for result in results:
            precedent_text = f"{result['payload'].get('name', '')}. {result['payload'].get('description', '')}"
            pairs.append([query_text, precedent_text])
        
        rerank_scores = self.reranker.predict(pairs)
        
        for i, result in enumerate(results):
            result['rerank_score'] = float(rerank_scores[i])
        
        results.sort(key=lambda x: x['rerank_score'], reverse=True)
        
        return results
    
    def match_precedent(
        self, 
        petition_type: str, 
        tribunal: str, 
        facts: str, 
        requests: str
    ) -> Dict[str, Any]:
        
        query_text = self.prepare_query_text(facts, requests)
        
        chunks = self.chunk_text(query_text)
        
        all_results = []
        
        for chunk in chunks:
            query_vector = self.encoder.encode(chunk).tolist()
            
            results = self.vector_search(query_vector)
            
            if tribunal:
                results = self.filter_by_tribunal(results, tribunal)
            
            all_results.extend(results)
        
        unique_results = {}
        for result in all_results:
            result_id = result['id']
            if result_id not in unique_results or result['score'] > unique_results[result_id]['score']:
                unique_results[result_id] = result
        
        all_results = list(unique_results.values())
        
        all_results.sort(key=lambda x: x['score'], reverse=True)
        all_results = all_results[:self.top_k]
        
        if all_results:
            all_results = self.rerank_results(query_text, all_results)
            all_results = all_results[:self.final_k]

        all_results.sort(key=lambda x: (x['score'], x.get('rerank_score', 0)), reverse=True)
        
        return {
            'query': {
                'type': petition_type,
                'tribunal': tribunal,
                'facts': facts[:200] + '...' if len(facts) > 200 else facts,
                'requests': requests[:200] + '...' if len(requests) > 200 else requests
            },
            'results': [
                {
                    'id': r['id'],
                    'name': r['payload'].get('name'),
                    'tribunal': r['payload'].get('tribunal'),
                    'situation': r['payload'].get('situation'),
                    'description': r['payload'].get('description'),
                    'url': r['payload'].get('url'),
                    'similarity_score': float(r['score']),
                    'rerank_score': r.get('rerank_score', 0.0)
                }
                for r in all_results
            ],
            'total_found': len(all_results)
        }