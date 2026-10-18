from datetime import date, timedelta
from flask import Blueprint, jsonify, request
from auth import auth
from db import q
from services.estoque import DIAS_ALERTA, status_lote

bp = Blueprint("estoque", __name__, url_prefix="/api")


@bp.get("/estoque")
@auth()
def listar():
    """Estoque por lote, com status de validade (ok, vence_em_breve, vencido)."""
    lotes = q("SELECT l.id,p.nome AS produto,p.tipo,l.codigo_lote,l.validade,l.quantidade FROM lotes l "
              "JOIN produtos p ON p.id=l.produto_id WHERE l.quantidade>0 AND p.nome LIKE ? "
              "ORDER BY l.validade", (f"%{request.args.get('q', '').strip()}%",))
    hoje = date.today()
    for l in lotes:
        l["status"] = status_lote(l["validade"], hoje)
    if request.args.get("status"):
        lotes = [l for l in lotes if l["status"] == request.args["status"]]
    return jsonify(lotes)


@bp.get("/dashboard")
@auth("admin", "farmaceutico")
def dashboard():
    hoje = date.today()
    limite = (hoje + timedelta(days=DIAS_ALERTA)).isoformat()
    h = hoje.isoformat()
    base_lote = ("SELECT p.nome AS produto,l.codigo_lote,l.validade,l.quantidade FROM lotes l "
                 "JOIN produtos p ON p.id=l.produto_id WHERE l.quantidade>0 AND ")
    return jsonify({
        "total_produtos": q("SELECT COUNT(*) AS n FROM produtos", one=True)["n"],
        "vendas_hoje": q("SELECT COALESCE(SUM(valor_total),0) AS t FROM vendas WHERE substr(data,1,10)=?", (h,), one=True)["t"],
        "faturamento_30d": q("SELECT COALESCE(SUM(valor_total),0) AS t FROM vendas WHERE substr(data,1,10)>=?",
                             ((hoje - timedelta(days=30)).isoformat(),), one=True)["t"],
        "estoque_baixo": q("SELECT * FROM (SELECT p.nome AS produto,p.estoque_minimo,"
                           "COALESCE((SELECT SUM(quantidade) FROM lotes WHERE produto_id=p.id AND validade>=?),0) AS disponivel "
                           "FROM produtos p) WHERE disponivel < estoque_minimo ORDER BY produto", (h,)),
        "vencendo": q(base_lote + "l.validade>=? AND l.validade<=? ORDER BY l.validade", (h, limite)),
        "vencidos": q(base_lote + "l.validade<? ORDER BY l.validade", (h,)),
        "vendas_por_dia": q("SELECT substr(data,1,10) AS dia,ROUND(SUM(valor_total),2) AS total FROM vendas "
                            "WHERE substr(data,1,10)>=? GROUP BY dia ORDER BY dia",
                            ((hoje - timedelta(days=6)).isoformat(),)),
    })
