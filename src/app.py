from os import name

from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Habilita CORS para permitir requisições do Angular

# Aqui definimos o nome do arquivo. O 'instance/' garante que ele fique na pasta correta
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///streetmodel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Configurações de Segurança
app.config["JWT_SECRET_KEY"] = "sua_chave_secreta_super_segura_aqui" 
jwt = JWTManager(app)

# Simulação de usuário administrador no banco de dados (Donos da loja)
# Na produção, você buscará isso via query SQL: SELECT * FROM usuarios WHERE ...
ADMIN_USERNAME = "alexsander"
ADMIN_PASSWORD_HASH = generate_password_hash("alexsander1166")

@app.route("/api/login", methods=["POST"])
def login():
    dados = request.get_json()
    username = dados.get("username")
    password = dados.get("password")

    if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
        # Cria o Token JWT válido por algumas horas
        token = create_access_token(identity=username)
        return jsonify(token=token), 200
    
    return jsonify(mensagem="Credenciais inválidas!"), 401

# Certifique-se de que o seu modelo tem o campo 'isNewRelease' para os lançamentos
class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    imageUrl = db.Column(db.String(200), nullable=False)
    isNewRelease = db.Column(db.Boolean, default=False)

# ROTAS DO CATÁLOGO PROTEGIDAS
@app.route("/api/produtos", methods=["POST"])
@jwt_required() # Só entra se enviar o cabeçalho "Authorization: Bearer <TOKEN>"
def adicionar_produto():
    # 1. Captura os dados enviados pelo formulário do Angular
    dados = request.get_json()
    
    # 2. Validação de segurança (evita salvar dados vazios no banco)
    if not dados or not dados.get('name') or not dados.get('price') or not dados.get('imageUrl'):
        return jsonify(mensagem="Erro: Todos os campos obrigatórios devem ser preenchidos!"), 400
        
    try:
        # 3. Mapeia os dados do JSON para o objeto do Banco de Dados
        novo_produto = Produto(
            name=dados['name'],
            price=float(dados['price']), # Garante que o preço vai como número decimal
            imageUrl=dados['imageUrl'],
            isNewRelease=dados.get('isNewRelease', False) # Se não for enviado, assume False
        )
        
        # 4. Prepara a inserção (Equivalente ao comando SQL: INSERT INTO produto ...)
        db.session.add(novo_produto)
        
        # 5. PERSISTÊNCIA REAL: Grava definitivamente as alterações no arquivo .db
        db.session.commit()
        
        # Opcional: Saber qual administrador realizou a ação (auditoria)
        #usuario_admin = get_jwt_identity()
        #print(f"Produto cadastrado pelo administrador: {usuario_admin}")

        # Retorna sucesso e o ID do produto que acabou de ser gerado pelo banco
        return jsonify({
            "mensagem": "Produto adicionado com sucesso ao catálogo!",
            "id": novo_produto.id
        }), 201

    except Exception as e:
        # Caso ocorra algum erro (falta de energia, arquivo travado, etc)
        # O rollback cancela a operação para não corromper o arquivo .db
        db.session.rollback()
        return jsonify({"mensagem": f"Erro interno ao persistir no banco: {str(e)}"}), 500

# No seu arquivo app.py (Backend Flask)
@app.route("/api/produtos", methods=["GET"]) # Certifique-se que 'GET' está aqui
def listar_produtos():
    produtos = Produto.query.all() # Exemplo com SQLAlchemy
    # Converta para JSON aqui e retorne
    return { "produtos": [
        {
            'id': produto.id,
            'name': produto.name,
            'price': produto.price,
            'imageUrl': produto.imageUrl,
            'isNewRelease': produto.isNewRelease
        } for produto in produtos
    ] }, 200  

@app.route("/api/produtos/<int:id>", methods=["PUT"])
@jwt_required()
def editar_produto(id):
    dados_atualizados = request.get_json()
    # Código SQL para UPDATE produtos SET ... WHERE id = id
    return jsonify(mensagem="Produto atualizado!"), 200

@app.route("/api/produtos/<int:id>", methods=["DELETE"])
@jwt_required()
def remover_produto(id):
    # Código SQL para DELETE FROM produtos WHERE id = id
    return jsonify(mensagem="Produto removido do catálogo!"), 200


with app.app_context():
    db.create_all()
    print("Banco de dados 'streetmodel.db' gerado com sucesso!")
    
if __name__ == "__main__":
    app.run(debug=True)