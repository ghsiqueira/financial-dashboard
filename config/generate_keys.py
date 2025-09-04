import secrets

def generate_secret_keys():    
    secret_key = secrets.token_hex(32)
    jwt_secret = secrets.token_hex(32)
    
    print("🔐 CHAVES SECRETAS GERADAS:")
    print("=" * 50)
    print(f"SECRET_KEY={secret_key}")
    print(f"JWT_SECRET_KEY={jwt_secret}")
    print("=" * 50)
    print("\n📝 Cole essas linhas no seu arquivo .env")
    
    # Opcionalmente salvar em arquivo
    with open('.env.example', 'w') as f:
        f.write(f"""# Configurações do Flask
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY={secret_key}
JWT_SECRET_KEY={jwt_secret}
MONGODB_URI=mongodb+srv://admin:admin@dash.rrduxag.mongodb.net/?retryWrites=true&w=majority&appName=dash

# Email (opcional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=seu-email@gmail.com
MAIL_PASSWORD=sua-senha-app
""")
    print("✅ Arquivo .env.example criado!")

if __name__ == "__main__":
    generate_secret_keys()