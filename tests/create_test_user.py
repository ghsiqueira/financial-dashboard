import sys
import os
from datetime import datetime, timedelta
import random

# Corrigir o path para encontrar o módulo app
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

# Adicionar a raiz do projeto ao Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Mudar para o diretório raiz do projeto
os.chdir(project_root)

def create_test_user():
    try:
        print(f"📁 Diretório de trabalho: {os.getcwd()}")
        print(f"🐍 Python path: {sys.path[0]}")
        
        # Agora importar os módulos
        from app import create_app, get_db, init_mongo
        from app.models import User, Transaction, Budget, Family
        
        # Criar app
        app = create_app()
        
        with app.app_context():
            # Inicializar mongo wrapper
            init_mongo()
            
            print("🚀 Criando usuário de teste...")
            
            # Obter instância do banco
            db = get_db()
            
            # Verificar se usuário já existe
            existing_user = User.find_by_email('demo@financedash.com')
            if existing_user:
                print("⚠️  Usuário demo@financedash.com já existe!")
                choice = input("Deseja recriar? (s/n): ").lower()
                if choice != 's':
                    print("❌ Operação cancelada.")
                    return
                
                # Remover usuário existente
                db.users.delete_one({'email': 'demo@financedash.com'})
                if hasattr(existing_user, '_id'):
                    db.transactions.delete_many({'added_by': existing_user._id})
                    db.budgets.delete_many({'owner_id': existing_user._id})
                print("🗑️  Dados anteriores removidos.")
            
            # Criar usuário demo
            demo_user = User('demo@financedash.com', 'Usuário Demo')
            demo_user.set_password('demo123')
            user_id = demo_user.save()
            
            print(f"✅ Usuário criado com ID: {user_id}")
            
            # Criar transações de exemplo
            print("📊 Criando transações de exemplo...")
            
            categories_receitas = ['Salário', 'Freelance', 'Investimentos', 'Vendas']
            categories_despesas = ['Alimentação', 'Transporte', 'Moradia', 'Saúde', 
                                 'Educação', 'Lazer', 'Vestuário', 'Tecnologia']
            
            transactions_created = 0
            
            # Criar transações dos últimos 6 meses
            for i in range(180):  # 180 dias
                date = datetime.now() - timedelta(days=i)
                
                # 70% chance de ter transação por dia
                if random.random() < 0.7:
                    # Receitas (20% das transações)
                    if random.random() < 0.2:
                        transaction = Transaction(
                            owner_type='individual',
                            owner_id=user_id,
                            added_by=user_id,
                            trans_type='income',
                            amount=random.uniform(500, 5000),
                            category=random.choice(categories_receitas),
                            description=f'Receita - {random.choice(categories_receitas)}'
                        )
                        transaction.date = date
                        transaction.save()
                        transactions_created += 1
                    
                    # Despesas (80% das transações)
                    else:
                        transaction = Transaction(
                            owner_type='individual',
                            owner_id=user_id,
                            added_by=user_id,
                            trans_type='expense',
                            amount=random.uniform(10, 800),
                            category=random.choice(categories_despesas),
                            description=f'Gasto em {random.choice(categories_despesas)}'
                        )
                        transaction.date = date
                        transaction.save()
                        transactions_created += 1
            
            print(f"✅ {transactions_created} transações criadas!")
            
            # Criar orçamentos de exemplo
            print("💰 Criando orçamentos de exemplo...")
            
            budgets_data = [
                {'category': 'Alimentação', 'limit': 800},
                {'category': 'Transporte', 'limit': 400},
                {'category': 'Lazer', 'limit': 300},
                {'category': 'Saúde', 'limit': 200},
                {'category': 'Vestuário', 'limit': 250}
            ]
            
            budgets_created = 0
            for budget_data in budgets_data:
                budget = Budget(
                    owner_id=user_id,
                    owner_type='individual',
                    category=budget_data['category'],
                    limit_amount=budget_data['limit'],
                    period='monthly'
                )
                budget.save()
                budgets_created += 1
            
            print(f"✅ {budgets_created} orçamentos criados!")
            
            # Criar família de exemplo
            print("👨‍👩‍👧‍👦 Criando família de exemplo...")
            
            family = Family('Família Demo', 'Família para demonstração', user_id)
            family.add_member(user_id, 'admin')
            family_id = family.save()
            
            # Adicionar família ao usuário
            db.users.update_one(
                {'_id': user_id},
                {
                    '$push': {'families': family_id},
                    '$set': {'default_family': family_id}
                }
            )
            
            # Criar algumas transações familiares
            for i in range(20):
                date = datetime.now() - timedelta(days=random.randint(0, 60))
                
                transaction = Transaction(
                    owner_type='family',
                    owner_id=family_id,
                    added_by=user_id,
                    trans_type=random.choice(['income', 'expense']),
                    amount=random.uniform(50, 1000),
                    category=random.choice(categories_receitas + categories_despesas),
                    description=f'Transação familiar - {random.choice(["Supermercado", "Combustível", "Internet", "Restaurante"])}'
                )
                transaction.date = date
                transaction.save()
            
            print("✅ Família e transações familiares criadas!")
            
            print("\n🎉 USUÁRIO DE TESTE CRIADO COM SUCESSO!")
            print("=" * 50)
            print("📧 Email: demo@financedash.com")
            print("🔑 Senha: demo123")
            print("=" * 50)
            print("\n🚀 Para testar:")
            print("1. Execute: python run.py")
            print("2. Acesse: http://localhost:5000")
            print("3. Faça login com os dados acima")
            print("\n💡 O usuário já tem:")
            print(f"   • {transactions_created} transações")
            print(f"   • {budgets_created} orçamentos")
            print("   • 1 família com transações")
            print("   • Dados dos últimos 6 meses")
            
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print(f"📁 Diretório atual: {os.getcwd()}")
        print(f"📁 Python path: {sys.path[:3]}...")
        print("\nVerifique se:")
        print("1. Você está executando da raiz do projeto")
        print("2. O arquivo app/__init__.py existe")
        print("3. As dependências estão instaladas")
        print("4. O arquivo .env está configurado")
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

def create_admin_user():
    """Criar usuário administrador"""
    try:
        from app import create_app, get_db, init_mongo
        from app.models import User
        
        app = create_app()
        
        with app.app_context():
            # Inicializar mongo wrapper
            init_mongo()
            
            print("👑 Criando usuário administrador...")
            
            email = input("Email do admin: ").strip()
            name = input("Nome do admin: ").strip()
            password = input("Senha do admin: ").strip()
            
            if not email or not name or not password:
                print("❌ Todos os campos são obrigatórios!")
                return
            
            # Verificar se já existe
            existing = User.find_by_email(email)
            if existing:
                print("❌ Usuário já existe!")
                return
            
            # Criar usuário
            admin_user = User(email, name)
            admin_user.set_password(password)
            user_id = admin_user.save()
            
            print(f"✅ Usuário administrador criado!")
            print(f"📧 Email: {email}")
            print(f"🔑 Senha: {password}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

def test_imports():
    """Testar se os imports funcionam"""
    try:
        print("🧪 Testando imports...")
        print(f"📁 Diretório atual: {os.getcwd()}")
        print(f"🐍 Python path: {sys.path[0]}")
        
        # Testar import do Flask
        print("   • Testando Flask...")
        import flask
        print("   ✅ Flask OK")
        
        # Testar import do app
        print("   • Testando app...")
        from app import create_app
        print("   ✅ App OK")
        
        # Testar criação do app
        print("   • Testando create_app...")
        app = create_app()
        print("   ✅ Create app OK")
        
        # Testar models
        print("   • Testando models...")
        from app.models import User
        print("   ✅ Models OK")
        
        # Testar contexto do app
        print("   • Testando app context...")
        with app.app_context():
            from app import get_db, init_mongo
            init_mongo()
            db = get_db()
            print(f"   ✅ Database conectado: {db.name}")
        
        print("\n✅ Todos os imports funcionaram!")
        return True
        
    except Exception as e:
        print(f"\n❌ Erro no teste de imports: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mongodb_connection():
    """Testar conexão específica com MongoDB"""
    try:
        print("🗄️  Testando conexão MongoDB...")
        
        from pymongo import MongoClient
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        mongo_uri = os.environ.get('MONGO_URI')
        print(f"   • URI: {mongo_uri}")
        
        if not mongo_uri:
            print("   ❌ MONGO_URI não encontrada no .env")
            return False
        
        client = MongoClient(mongo_uri)
        
        # Testar ping
        print("   • Testando ping...")
        info = client.admin.command('ping')
        print(f"   ✅ Ping OK: {info}")
        
        # Testar acesso ao banco
        print("   • Testando banco 'financedash'...")
        db = client['financedash']
        collections = db.list_collection_names()
        print(f"   ✅ Banco OK. Collections: {collections}")
        
        # Testar inserção
        print("   • Testando inserção...")
        test_collection = db['test']
        result = test_collection.insert_one({'test': True, 'timestamp': datetime.now()})
        print(f"   ✅ Inserção OK: {result.inserted_id}")
        
        # Limpar teste
        test_collection.delete_one({'_id': result.inserted_id})
        print("   ✅ Teste de limpeza OK")
        
        client.close()
        print("\n✅ Conexão MongoDB funcionando perfeitamente!")
        return True
        
    except Exception as e:
        print(f"\n❌ Erro na conexão MongoDB: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🏦 DASHBOARD FINANCEIRO - CRIADOR DE USUÁRIOS")
    print("=" * 50)
    print("1. Criar usuário de demonstração (recomendado)")
    print("2. Criar usuário personalizado")
    print("3. Testar imports")
    print("4. Testar conexão MongoDB")
    print("5. Sair")
    
    try:
        choice = input("\nEscolha uma opção (1-5): ").strip()
        
        if choice == '1':
            create_test_user()
        elif choice == '2':
            create_admin_user()
        elif choice == '3':
            test_imports()
        elif choice == '4':
            test_mongodb_connection()
        elif choice == '5':
            print("👋 Tchau!")
        else:
            print("❌ Opção inválida!")
            
    except KeyboardInterrupt:
        print("\n\n👋 Operação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")

if __name__ == '__main__':
    main()
