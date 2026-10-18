from datetime import datetime, timedelta, timezone
from functools import wraps
import jwt
from flask import current_app, g, jsonify, request


def erro(msg, codigo=400):
    return jsonify({"erro": msg}), codigo


def gerar_token(usuario):
    payload = {
        "sub": str(usuario["id"]),
        "perfil": usuario["perfil"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def auth(*perfis):
    """Decorator: exige token JWT válido e (opcionalmente) um dos perfis informados."""
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            cabecalho = request.headers.get("Authorization", "")
            if not cabecalho.startswith("Bearer "):
                return erro("Token ausente", 401)
            try:
                p = jwt.decode(cabecalho[7:], current_app.config["SECRET_KEY"], algorithms=["HS256"])
            except jwt.PyJWTError:
                return erro("Token inválido ou expirado", 401)
            g.user = {"id": int(p["sub"]), "perfil": p["perfil"]}
            if perfis and g.user["perfil"] not in perfis:
                return erro("Acesso negado para este perfil", 403)
            return f(*args, **kwargs)
        return wrapper
    return decorador
