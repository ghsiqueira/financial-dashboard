from flask import Flask, redirect, url_for, render_template
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from pymongo import MongoClient
from config import Config

# Extensões globais
bcrypt = Bcrypt()
jwt = JWTManager()
mail = Mail()
mongo_client = None
db = None

def create_app(config_class=Config):
    global mongo_client, db
    
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Conectar ao MongoDB usando pymongo direto
    try:
        mongo_uri = app.config.get('MONGO_URI')
        print(f"🔗 Conectando ao MongoDB: {mongo_uri}")
        
        mongo_client = MongoClient(mongo_uri)
        
        # CORRIGIDO: Especificar o nome do banco explicitamente
        db_name = 'financedash'  # Nome do banco definido aqui
        db = mongo_client[db_name]
        
        # Testar conexão
        info = mongo_client.admin.command('ping')
        print(f"✅ MongoDB conectado com sucesso: {info}")
        print(f"📦 Banco de dados: {db_name}")
        
    except Exception as e:
        print(f"❌ Erro ao conectar MongoDB: {e}")
        raise
    
    # Inicializar outras extensões
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    
    # Registrar Blueprints
    from app.auth.routes import auth
    from app.dashboard.routes import dashboard
    from app.transactions.routes import transactions
    from app.family.routes import family
    from app.budgets.routes import budgets
    from app.reports.routes import reports
    from app.notifications.routes import notifications
    
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(dashboard, url_prefix='/dashboard')
    app.register_blueprint(transactions, url_prefix='/transactions')
    app.register_blueprint(family, url_prefix='/family')
    app.register_blueprint(budgets, url_prefix='/budgets')
    app.register_blueprint(reports, url_prefix='/reports')
    app.register_blueprint(notifications, url_prefix='/notifications')
    
    # Rota principal
    @app.route('/')
    def index():
        from flask import session
        if 'user_id' in session:
            return redirect(url_for('dashboard.overview'))
        else:
            return redirect(url_for('auth.login'))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
    
    # Template globals
    @app.template_global()
    def format_currency(amount):
        return f"R$ {amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    @app.template_global()
    def format_date(date):
        return date.strftime('%d/%m/%Y') if date else ''
    
    return app

def get_db():
    """Retorna a instância do banco de dados"""
    return db

# ADICIONADO: Classe para compatibilidade com Flask-PyMongo
class MongoWrapper:
    """Wrapper para simular Flask-PyMongo"""
    def __init__(self):
        self.db = None
    
    def init_app(self, app):
        global db
        self.db = db

# Instância global para compatibilidade
mongo = MongoWrapper()

def init_mongo():
    """Inicializa o wrapper do mongo após a criação do app"""
    global mongo, db
    mongo.db = db