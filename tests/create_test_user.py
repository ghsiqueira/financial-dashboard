#!/usr/bin/env python3
"""
Script para criar usuário de teste no Dashboard Financeiro
Execute: python create_test_user.py
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_user():
    try:
        from app import create_app, mongo
        from app.models import User, Transaction, Budget, Family
        
        # Criar app
        app = create_app()
        
        with app.app_context():
            print("🚀 Criando usuário de teste...")
            
            # Verificar se usuário já existe
            existing_user = User.find_by_email('demo@financedash.com')
            if existing_user:
                print("⚠️  Usuário demo@financedash.com já existe!")
                choice = input("Deseja recriar? (s/n): ").lower()
                if choice != 's':
                    print("❌ Operação cancelada.")
                    return
                
                # Remover usuário existente
                mongo.db.users.delete_one({'email': 'demo@financedash.com'})
                mongo.db.transactions.delete_many({'added_by': existing_user._id})
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
            mongo.db.users.update_one(
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
            print("\n📁 Certifique-se de executar este script da raiz do projeto:")
            print("   python tests/create_test_user.py")
            
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print("Certifique-se de que está no diretório correto e instalou as dependências")
    except Exception as e:
        print(f"❌ Erro: {e}")

def create_admin_user():
    """Criar usuário administrador"""
    try:
        from app import create_app
        from app.models import User
        
        app = create_app()
        
        with app.app_context():
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

def main():
    print("🏦 DASHBOARD FINANCEIRO - CRIADOR DE USUÁRIOS")
    print("=" * 50)
    print("1. Criar usuário de demonstração (recomendado)")
    print("2. Criar usuário personalizado")
    print("3. Sair")
    
    try:
        choice = input("\nEscolha uma opção (1-3): ").strip()
        
        if choice == '1':
            create_test_user()
        elif choice == '2':
            create_admin_user()
        elif choice == '3':
            print("👋 Tchau!")
        else:
            print("❌ Opção inválida!")
            
    except KeyboardInterrupt:
        print("\n\n👋 Operação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")

if __name__ == '__main__':
    main()