import json
import time
from flask import Blueprint, Response, request, jsonify, stream_with_context
from src.core.matcher import PrecedentMatcher

match_bp = Blueprint("match", __name__)

matcher: PrecedentMatcher = None


def init_matcher(qdrant_client, collection_name, model_name):
    """Inicializa o matcher com as dependências."""
    global matcher
    matcher = PrecedentMatcher(qdrant_client, collection_name, model_name)


# ---------------------------------------------------------------------------
# Helpers SSE
# ---------------------------------------------------------------------------

def _sse_event(event: str, data: dict) -> str:
    """Formata um evento SSE conforme a especificação (event + data + \n\n)."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _sse_keepalive() -> str:
    """Comentário SSE para evitar timeout de proxies/load balancers."""
    return ": keepalive\n\n"


# ---------------------------------------------------------------------------
# POST /api/match  — resposta síncrona (mantida para compatibilidade)
# ---------------------------------------------------------------------------

@match_bp.route("/match", methods=["POST"])
def match_precedent():
    """
    Endpoint síncrono de matching de precedentes.

    Body esperado:
    {
        "type": "herança",
        "tribunal": "STJ",   # opcional
        "facts": "...",
        "requests": "..."
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "JSON inválido"}), 400

        petition_type = data.get("type")
        tribunal = data.get("tribunal")
        facts = data.get("facts", "")
        req = data.get("requests", "")

        if not petition_type:
            return jsonify({"error": 'Campo "type" é obrigatório'}), 400

        if not facts and not req:
            return jsonify(
                {"error": 'É necessário fornecer "facts" ou "requests"'}
            ), 400

        result = matcher.match_precedent(
            petition_type=petition_type,
            tribunal=tribunal,
            facts=facts,
            requests=req,
        )

        return jsonify(result), 200

    except Exception as e:
        print(f"Erro no endpoint /match: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/match/stream  — resposta SSE (novo)
# ---------------------------------------------------------------------------

@match_bp.route("/match/stream", methods=["POST"])
def match_precedent_stream():
    """
    Endpoint SSE de matching de precedentes.

    Aceita o mesmo body que /match, mas devolve um stream de eventos
    Server-Sent Events ao invés de uma resposta JSON única.

    Eventos emitidos:
      event: search_complete   → {"total": <int>}
      event: rerank_complete   → {"total": <int>}
      event: precedent         → {resultado completo + "index": <int>}
      event: done              → {"total_found": <int>}
      event: error             → {"message": "<string>"}

    O campo "index" em cada evento "precedent" indica a posição original
    no ranking (0-based), permitindo ao cliente reordenar se necessário.
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "JSON inválido"}), 400

        petition_type = data.get("type")
        tribunal = data.get("tribunal")
        facts = data.get("facts", "")
        req = data.get("requests", "")

        if not petition_type:
            return jsonify({"error": 'Campo "type" é obrigatório'}), 400

        if not facts and not req:
            return jsonify(
                {"error": 'É necessário fornecer "facts" ou "requests"'}
            ), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 400

    def generate():
        # Keepalive imediato para que o cliente saiba que a conexão abriu.
        yield _sse_keepalive()

        events: list[tuple[str, dict]] = []

        def emit(event_name: str, payload: dict) -> None:
            """
            Callback chamado pelo matcher conforme cada etapa termina.
            Adiciona o evento à fila para ser consumido pelo generator.
            """
            events.append((event_name, payload))

        # Roda o pipeline em uma thread separada para não bloquear o
        # generator enquanto o ThreadPoolExecutor do matcher trabalha.
        import threading

        pipeline_done = threading.Event()
        pipeline_error: list[Exception] = []

        def run_pipeline():
            try:
                matcher.match_precedent_stream(
                    petition_type=petition_type,
                    tribunal=tribunal,
                    facts=facts,
                    requests=req,
                    emit=emit,
                )
            except Exception as exc:
                pipeline_error.append(exc)
            finally:
                pipeline_done.set()

        thread = threading.Thread(target=run_pipeline, daemon=True)
        thread.start()

        last_event_idx = 0

        # Consome eventos à medida que são produzidos, emitindo keepalives
        # enquanto aguarda para não deixar o cliente sem dados.
        while not pipeline_done.is_set() or last_event_idx < len(events):
            # Entrega todos os eventos que já chegaram
            while last_event_idx < len(events):
                event_name, payload = events[last_event_idx]
                yield _sse_event(event_name, payload)
                last_event_idx += 1

            if not pipeline_done.is_set():
                # Aguarda um pouco antes de checar novamente
                time.sleep(0.05)
                yield _sse_keepalive()

        if pipeline_error:
            yield _sse_event("error", {"message": str(pipeline_error[0])})

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            # Desabilita buffering em proxies Nginx/uWSGI
            "X-Accel-Buffering": "no",
            # Permite requisições cross-origin do front
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------

@match_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify(
        {"status": "healthy", "matcher_initialized": matcher is not None}
    ), 200
