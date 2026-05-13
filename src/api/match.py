from flask import Blueprint, request, jsonify
from src.core.matcher import PrecedentMatcher

match_bp = Blueprint("match", __name__)

matcher = None


def init_matcher(qdrant_client, collection_name, model_name):
    """Inicializa o matcher com as dependências"""
    global matcher
    matcher = PrecedentMatcher(qdrant_client, collection_name, model_name)


@match_bp.route("/match", methods=["POST"])
def match_precedent():
    """
    Endpoint para matching de precedentes

    Body esperado:
    {
        "type": "herança",
        "tribunal": "STJ",  # opcional
        "facts": "texto dos fatos...",
        "requests": "texto dos pedidos..."
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "JSON inválido"}), 400

        petition_type = data.get("type")
        tribunal = data.get("tribunal")
        facts = data.get("facts", "")
        requests = data.get("requests", "")

        if not petition_type:
            return jsonify({"error": 'Campo "type" é obrigatório'}), 400

        if not facts and not requests:
            return jsonify(
                {"error": 'É necessário fornecer "facts" ou "requests"'}
            ), 400

        # Realiza o matching
        result = matcher.match_precedent(
            petition_type=petition_type,
            tribunal=tribunal,
            facts=facts,
            requests=requests,
        )

        return jsonify(result), 200

    except Exception as e:
        print(f"Erro no endpoint /match: {e}")
        return jsonify({"error": str(e)}), 500


@match_bp.route("/health", methods=["GET"])
def health_check():
    """Endpoint para verificar saúde do serviço"""
    return jsonify(
        {"status": "healthy", "matcher_initialized": matcher is not None}
    ), 200
