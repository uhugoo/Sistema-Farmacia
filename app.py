
import os
from flask import Flask, jsonify, render_template
from db import close_db, init_db


def create_app(config=None):
    app = Flask(__name__)

    # Permite configurar o local do banco pelo Render
    database_path = os.environ.get(
        "DATABASE_PATH",
        os.path.join(app.root_path, "farmacia.db")
    )

    os.makedirs(os.path.dirname(database_path), exist_ok=True)

    app.config["DATABASE"] = database_path

    # Chave secreta configurada nas variáveis de ambiente
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "chave-local-apenas-para-desenvolvimento"
    )

    if config:
        app.config.update(config)

    app.teardown_appcontext(close_db)

    from routes import usuarios, produtos, compras, vendas, estoque

    for modulo in (usuarios, produtos, compras, vendas, estoque):
        app.register_blueprint(modulo.bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(404)
    def nao_encontrado(_):
        return jsonify({"erro": "Rota não encontrada"}), 404

    with app.app_context():
        init_db(app.config.get("USUARIOS_PADRAO", True))

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
