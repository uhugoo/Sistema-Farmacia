import sqlite3
from flask import Blueprint, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash
import validators as v
from auth import auth, erro, gerar_token
from db import q, run

bp = Blueprint("usuarios", __name__, url_prefix="/api")


@bp.post("/auth/login")
def login():
    d = request.get_json(silent=True) or {}
    u = q("SELECT * FROM usuarios WHERE email=?", ((d.get("email") or "").strip().lower(),), one=True)
    if not u or not check_password_hash(u["senha_hash"], d.get("senha") or ""):
        return erro("E-mail ou senha incorretos", 401)
    if not u["ativo"]:
        return erro("Usuário inativo", 403)
    return jsonify({"token": gerar_token(u), "id": u["id"], "nome": u["nome_completo"], "perfil": u["perfil"]})


@bp.get("/usuarios")
@auth("admin")
def listar():
    busca = f"%{request.args.get('q', '').strip()}%"
    sql = ("SELECT id,nome_completo,email,telefone,perfil FROM usuarios "
           "WHERE (nome_completo LIKE ? OR email LIKE ?)")
    args = [busca, busca]
    if request.args.get("perfil") in v.PERFIS:
        sql += " AND perfil=?"
        args.append(request.args["perfil"])
    return jsonify(q(sql + " ORDER BY nome_completo", args))


@bp.post("/usuarios")
@auth("admin")
def criar():
    d = request.get_json(silent=True) or {}
    nome = (d.get("nome_completo") or "").strip()
    email = (d.get("email") or "").strip().lower()
    for msg in (v.nome(nome), v.email(email), v.telefone(d.get("telefone")), v.senha(d.get("senha"))):
        if msg:
            return erro(msg)
    if d.get("perfil") not in v.PERFIS:
        return erro("Perfil inválido (admin, farmaceutico ou atendente)")
    if q("SELECT 1 FROM usuarios WHERE email=?", (email,), one=True):
        return erro("E-mail já cadastrado", 409)
    uid = run("INSERT INTO usuarios(nome_completo,email,telefone,senha_hash,perfil) VALUES(?,?,?,?,?)",
              (nome, email, d["telefone"], generate_password_hash(d["senha"]), d["perfil"]))
    return jsonify({"id": uid}), 201


@bp.delete("/usuarios/<int:uid>")
@auth("admin")
def remover(uid):
    if uid == g.user["id"]:
        return erro("Você não pode remover o próprio usuário")
    if not q("SELECT 1 FROM usuarios WHERE id=?", (uid,), one=True):
        return erro("Usuário não encontrado", 404)
    try:
        run("DELETE FROM usuarios WHERE id=?", (uid,))
    except sqlite3.IntegrityError:
        return erro("Usuário possui compras ou vendas registradas e não pode ser removido", 409)
    return jsonify({"ok": True})
