from flask import Blueprint, flash, render_template, request, session, redirect, url_for, jsonify
from app.auth.routes import login_required
from app.models import User, Transaction, Budget, Family
from app.dashboard.charts import generate_charts_data
from datetime import datetime, timedelta
import calendar

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/overview')
@login_required
def overview():
    try:
        user_id = session['user_id']
        print(f"🔍 Dashboard overview iniciado para user_id: {user_id}")
        
        user = User.find_by_id(user_id)
        
        if not user:
            print(f"❌ Usuário não encontrado para ID: {user_id}")
            session.clear()
            return redirect(url_for('auth.login'))
        
        print(f"✅ Usuário encontrado: {user.name}")
        
        # 🔥 SEMPRE obter famílias do usuário
        user_families = get_user_families(user)
        print(f"📊 Famílias encontradas: {len(user_families)}")
        
        # Determinar conta ativa (individual ou família)
        active_account = request.args.get('account', 'individual')
        active_family_id = None
        
        if active_account == 'family' and hasattr(user, 'default_family') and user.default_family:
            active_family_id = user.default_family
            owner_type = 'family'
            owner_id = active_family_id
        else:
            owner_type = 'individual'
            owner_id = user_id
        
        print(f"🎯 Conta ativa: {active_account}, Owner: {owner_type}")
        
        # Resumo do mês atual - COM PROTEÇÃO
        try:
            monthly_summary = Transaction.get_monthly_summary(owner_id, owner_type)
            print(f"💰 Resumo mensal carregado: {monthly_summary}")
        except Exception as e:
            print(f"Erro ao obter resumo mensal: {e}")
            monthly_summary = {'income': 0, 'expense': 0, 'balance': 0}
        
        # Transações recentes - COM PROTEÇÃO
        try:
            recent_transactions = Transaction.get_user_transactions(
                user_id, owner_type, owner_id, limit=10
            )
            print(f"📝 Transações recentes: {len(recent_transactions)}")
        except Exception as e:
            print(f"Erro ao obter transações recentes: {e}")
            recent_transactions = []
        
        # Dados para gráficos - COM PROTEÇÃO
        try:
            charts_data = generate_charts_data(owner_id, owner_type)
            print(f"📊 Gráficos gerados com sucesso")
        except Exception as e:
            print(f"Erro ao gerar gráficos: {e}")
            charts_data = {
                'expenses_pie': None,
                'monthly_evolution': None,
                'income_vs_expenses': None,
                'category_trends': None,
                'daily_spending': None
            }
        
        # Orçamentos - COM PROTEÇÃO
        try:
            budgets = get_user_budgets(owner_id, owner_type)
            print(f"💰 Orçamentos carregados: {len(budgets)}")
        except Exception as e:
            print(f"Erro ao obter orçamentos: {e}")
            budgets = []
        
        context = {
            'user': user,
            'user_families': user_families,  # 🔥 SEMPRE incluir
            'monthly_summary': monthly_summary,
            'recent_transactions': recent_transactions,
            'charts_data': charts_data,
            'budgets': budgets,
            'active_account': active_account,
            'active_family_id': str(active_family_id) if active_family_id else None
        }
        
        print(f"✅ Contexto montado com sucesso. Renderizando dashboard...")
        return render_template('dashboard/overview.html', **context)
        
    except Exception as e:
        print(f"❌ Erro geral no dashboard: {e}")
        import traceback
        traceback.print_exc()
        # Em caso de erro crítico, redirecionar para login
        session.clear()
        flash('Erro no sistema. Faça login novamente.', 'error')
        return redirect(url_for('auth.login'))

def get_user_families(user):
    """Função auxiliar para obter famílias do usuário"""
    user_families = []
    try:
        if user and hasattr(user, 'families') and user.families:
            for family_id in user.families:
                try:
                    family = Family.find_by_id(family_id)
                    if family:
                        user_families.append(family)
                except Exception as e:
                    print(f"Erro ao carregar família {family_id}: {e}")
                    continue
    except Exception as e:
        print(f"Erro ao obter famílias: {e}")
    return user_families

@dashboard.route('/transactions')
@login_required
def transactions():
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        # 🔥 SEMPRE obter famílias do usuário
        user_families = get_user_families(user)
        
        # Parâmetros de filtro
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        category = request.args.get('category')
        transaction_type = request.args.get('type')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Conta ativa
        active_account = request.args.get('account', 'individual')
        if active_account == 'family' and user.default_family:
            owner_type = 'family'
            owner_id = user.default_family
        else:
            owner_type = 'individual'
            owner_id = user_id
        
        # Buscar transações com filtros - COM PROTEÇÃO
        try:
            transactions = get_filtered_transactions(
                owner_id, owner_type, page, limit, category, 
                transaction_type, date_from, date_to
            )
        except Exception as e:
            print(f"Erro ao buscar transações: {e}")
            transactions = []
        
        # Categorias para filtro - COM PROTEÇÃO
        try:
            categories = get_categories(owner_id, owner_type)
        except Exception as e:
            print(f"Erro ao buscar categorias: {e}")
            categories = []
        
        context = {
            'user': user,
            'user_families': user_families,  # 🔥 SEMPRE incluir
            'transactions': transactions,
            'categories': categories,
            'active_account': active_account,
            'filters': {
                'category': category,
                'type': transaction_type,
                'date_from': date_from,
                'date_to': date_to
            }
        }
        
        return render_template('dashboard/transactions.html', **context)
        
    except Exception as e:
        print(f"Erro na página de transações: {e}")
        return redirect(url_for('dashboard.overview'))

@dashboard.route('/budgets')
@login_required
def budgets():
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        # 🔥 SEMPRE obter famílias do usuário
        user_families = get_user_families(user)
        
        # Conta ativa
        active_account = request.args.get('account', 'individual')
        if active_account == 'family' and user.default_family:
            owner_type = 'family'
            owner_id = user.default_family
        else:
            owner_type = 'individual'
            owner_id = user_id
        
        # Orçamentos - COM PROTEÇÃO
        try:
            budgets = get_user_budgets(owner_id, owner_type)
            
            # Atualizar valores gastos
            for budget in budgets:
                try:
                    budget_obj = Budget(owner_id, owner_type, budget['category'], budget['limit'])
                    budget_obj._id = budget['_id']
                    budget_obj.update_spent_amount()
                    budget['current_spent'] = budget_obj.current_spent
                    budget['percentage'] = (budget['current_spent'] / budget['limit']) * 100 if budget['limit'] > 0 else 0
                    budget['remaining'] = budget['limit'] - budget['current_spent']
                except Exception as e:
                    print(f"Erro ao atualizar orçamento {budget.get('_id')}: {e}")
                    budget['current_spent'] = 0
                    budget['percentage'] = 0
                    budget['remaining'] = budget['limit']
                    
        except Exception as e:
            print(f"Erro ao buscar orçamentos: {e}")
            budgets = []
        
        context = {
            'user': user,
            'user_families': user_families,  # 🔥 SEMPRE incluir
            'budgets': budgets,
            'active_account': active_account
        }
        
        return render_template('dashboard/budgets.html', **context)
        
    except Exception as e:
        print(f"Erro na página de orçamentos: {e}")
        return redirect(url_for('dashboard.overview'))

@dashboard.route('/reports')
@login_required
def reports():
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        # 🔥 SEMPRE obter famílias do usuário
        user_families = get_user_families(user)
        
        # Conta ativa
        active_account = request.args.get('account', 'individual')
        if active_account == 'family' and user.default_family:
            owner_type = 'family'
            owner_id = user.default_family
        else:
            owner_type = 'individual'
            owner_id = user_id
        
        # Período do relatório
        year = int(request.args.get('year', datetime.now().year))
        month = request.args.get('month')
        
        try:
            if month:
                month = int(month)
                report_data = generate_monthly_report(owner_id, owner_type, year, month)
                report_type = 'monthly'
            else:
                report_data = generate_yearly_report(owner_id, owner_type, year)
                report_type = 'yearly'
        except Exception as e:
            print(f"Erro ao gerar relatório: {e}")
            report_data = {}
            report_type = 'monthly'
        
        context = {
            'user': user,
            'user_families': user_families,  # 🔥 SEMPRE incluir
            'report_data': report_data,
            'report_type': report_type,
            'year': year,
            'month': month,
            'active_account': active_account
        }
        
        return render_template('dashboard/reports.html', **context)
        
    except Exception as e:
        print(f"Erro na página de relatórios: {e}")
        return redirect(url_for('dashboard.overview'))

# API endpoints
@dashboard.route('/api/summary')
@login_required
def api_summary():
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        active_account = request.args.get('account', 'individual')
        if active_account == 'family' and user.default_family:
            owner_type = 'family'
            owner_id = user.default_family
        else:
            owner_type = 'individual'
            owner_id = user_id
        
        summary = Transaction.get_monthly_summary(owner_id, owner_type)
        return jsonify(summary)
        
    except Exception as e:
        print(f"Erro na API summary: {e}")
        return jsonify({'income': 0, 'expense': 0, 'balance': 0}), 500

@dashboard.route('/api/charts/<chart_type>')
@login_required
def api_charts(chart_type):
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        active_account = request.args.get('account', 'individual')
        if active_account == 'family' and user.default_family:
            owner_type = 'family'
            owner_id = user.default_family
        else:
            owner_type = 'individual'
            owner_id = user_id
        
        if chart_type == 'expenses_by_category':
            data = get_expenses_by_category(owner_id, owner_type)
        elif chart_type == 'monthly_evolution':
            data = get_monthly_evolution(owner_id, owner_type)
        elif chart_type == 'income_vs_expenses':
            data = get_income_vs_expenses(owner_id, owner_type)
        else:
            data = {}
        
        return jsonify(data)
        
    except Exception as e:
        print(f"Erro na API charts: {e}")
        return jsonify({}), 500

# Funções auxiliares - COM PROTEÇÃO DE ERRO
def get_user_budgets(owner_id, owner_type):
    try:
        from app import get_db
        from bson.objectid import ObjectId
        
        db = get_db()
        budgets = db.budgets.find({
            'owner_id': ObjectId(owner_id),
            'owner_type': owner_type
        })
        return list(budgets)
    except Exception as e:
        print(f"Erro ao buscar orçamentos: {e}")
        return []

def get_filtered_transactions(owner_id, owner_type, page, limit, category, 
                            transaction_type, date_from, date_to):
    try:
        from app import get_db
        from bson.objectid import ObjectId
        
        db = get_db()
        query = {
            'owner_id': ObjectId(owner_id),
            'owner_type': owner_type
        }
        
        if category:
            query['category'] = category
        
        if transaction_type:
            query['type'] = transaction_type
        
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query['$gte'] = datetime.strptime(date_from, '%Y-%m-%d')
            if date_to:
                date_query['$lte'] = datetime.strptime(date_to, '%Y-%m-%d')
            query['date'] = date_query
        
        skip = (page - 1) * limit
        transactions = db.transactions.find(query).sort('date', -1).skip(skip).limit(limit)
        
        return list(transactions)
    except Exception as e:
        print(f"Erro ao filtrar transações: {e}")
        return []

def get_categories(owner_id, owner_type):
    try:
        from app import get_db
        from bson.objectid import ObjectId
        
        db = get_db()
        pipeline = [
            {'$match': {'owner_id': ObjectId(owner_id), 'owner_type': owner_type}},
            {'$group': {'_id': '$category'}},
            {'$sort': {'_id': 1}}
        ]
        
        result = db.transactions.aggregate(pipeline)
        return [item['_id'] for item in result if item['_id']]
    except Exception as e:
        print(f"Erro ao buscar categorias: {e}")
        return []

def get_expenses_by_category(owner_id, owner_type):
    try:
        from app import get_db
        from bson.objectid import ObjectId
        
        db = get_db()
        # Últimos 30 dias
        start_date = datetime.now() - timedelta(days=30)
        
        pipeline = [
            {
                '$match': {
                    'owner_id': ObjectId(owner_id),
                    'owner_type': owner_type,
                    'type': 'expense',
                    'date': {'$gte': start_date}
                }
            },
            {
                '$group': {
                    '_id': '$category',
                    'total': {'$sum': '$amount'},
                    'count': {'$sum': 1}
                }
            },
            {'$sort': {'total': -1}}
        ]
        
        result = list(db.transactions.aggregate(pipeline))
        
        return {
            'labels': [item['_id'] for item in result],
            'values': [item['total'] for item in result]
        }
    except Exception as e:
        print(f"Erro em expenses_by_category: {e}")
        return {'labels': [], 'values': []}

def get_monthly_evolution(owner_id, owner_type):
    try:
        from app import get_db
        from bson.objectid import ObjectId
        
        db = get_db()
        # Últimos 12 meses
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        pipeline = [
            {
                '$match': {
                    'owner_id': ObjectId(owner_id),
                    'owner_type': owner_type,
                    'date': {'$gte': start_date, '$lte': end_date}
                }
            },
            {
                '$group': {
                    '_id': {
                        'year': {'$year': '$date'},
                        'month': {'$month': '$date'},
                        'type': '$type'
                    },
                    'total': {'$sum': '$amount'}
                }
            },
            {'$sort': {'_id.year': 1, '_id.month': 1}}
        ]
        
        result = list(db.transactions.aggregate(pipeline))
        
        # Organizar dados para o gráfico
        months = []
        income_data = []
        expense_data = []
        
        # Criar estrutura dos últimos 12 meses
        current = start_date.replace(day=1)
        while current <= end_date:
            month_key = f"{current.year}-{current.month:02d}"
            months.append(month_key)
            
            # Buscar dados do mês
            month_income = 0
            month_expense = 0
            
            for item in result:
                if (item['_id']['year'] == current.year and 
                    item['_id']['month'] == current.month):
                    if item['_id']['type'] == 'income':
                        month_income = item['total']
                    elif item['_id']['type'] == 'expense':
                        month_expense = item['total']
            
            income_data.append(month_income)
            expense_data.append(month_expense)
            
            # Próximo mês
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        return {
            'labels': months,
            'income': income_data,
            'expenses': expense_data
        }
    except Exception as e:
        print(f"Erro em monthly_evolution: {e}")
        return {'labels': [], 'income': [], 'expenses': []}

def get_income_vs_expenses(owner_id, owner_type):
    try:
        from app import get_db
        from bson.objectid import ObjectId
        
        db = get_db()
        # Últimos 6 meses
        pipeline = [
            {
                '$match': {
                    'owner_id': ObjectId(owner_id),
                    'owner_type': owner_type,
                    'date': {'$gte': datetime.now() - timedelta(days=180)}
                }
            },
            {
                '$group': {
                    '_id': '$type',
                    'total': {'$sum': '$amount'}
                }
            }
        ]
        
        result = list(db.transactions.aggregate(pipeline))
        
        data = {'income': 0, 'expense': 0}
        for item in result:
            data[item['_id']] = item['total']
        
        return {
            'labels': ['Receitas', 'Despesas'],
            'values': [data['income'], data['expense']]
        }
    except Exception as e:
        print(f"Erro em income_vs_expenses: {e}")
        return {'labels': ['Receitas', 'Despesas'], 'values': [0, 0]}

def generate_monthly_report(owner_id, owner_type, year, month):
    try:
        from app import get_db
        from bson.objectid import ObjectId
        
        db = get_db()
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        # Resumo geral
        summary = Transaction.get_monthly_summary(owner_id, owner_type, year, month)
        
        # Gastos por categoria
        expenses_by_category = get_expenses_by_category_period(
            owner_id, owner_type, start_date, end_date
        )
        
        # Transações do período
        transactions = get_period_transactions(
            owner_id, owner_type, start_date, end_date
        )
        
        return {
            'period': f"{calendar.month_name[month]} {year}",
            'summary': summary,
            'expenses_by_category': expenses_by_category,
            'transactions': transactions,
            'total_transactions': len(transactions)
        }
    except Exception as e:
        print(f"Erro em generate_monthly_report: {e}")
        return {'period': '', 'summary': {}, 'expenses_by_category': [], 'transactions': [], 'total_transactions': 0}

def generate_yearly_report(owner_id, owner_type, year):
    try:
        from app import get_db
        from bson.objectid import ObjectId
        
        db = get_db()
        start_date = datetime(year, 1, 1)
        end_date = datetime(year + 1, 1, 1)
        
        # Resumo por mês
        monthly_summaries = []
        for month in range(1, 13):
            try:
                summary = Transaction.get_monthly_summary(owner_id, owner_type, year, month)
                summary['month'] = calendar.month_name[month]
                monthly_summaries.append(summary)
            except:
                monthly_summaries.append({
                    'month': calendar.month_name[month],
                    'income': 0,
                    'expense': 0,
                    'balance': 0
                })
        
        # Resumo anual
        total_income = sum(m['income'] for m in monthly_summaries)
        total_expenses = sum(m['expense'] for m in monthly_summaries)
        
        return {
            'year': year,
            'monthly_summaries': monthly_summaries,
            'annual_summary': {
                'income': total_income,
                'expense': total_expenses,
                'balance': total_income - total_expenses
            }
        }
    except Exception as e:
        print(f"Erro em generate_yearly_report: {e}")
        return {'year': year, 'monthly_summaries': [], 'annual_summary': {'income': 0, 'expense': 0, 'balance': 0}}

def get_expenses_by_category_period(owner_id, owner_type, start_date, end_date):
    try:
        from app import get_db
        from bson.objectid import ObjectId
        
        db = get_db()
        pipeline = [
            {
                '$match': {
                    'owner_id': ObjectId(owner_id),
                    'owner_type': owner_type,
                    'type': 'expense',
                    'date': {'$gte': start_date, '$lt': end_date}
                }
            },
            {
                '$group': {
                    '_id': '$category',
                    'total': {'$sum': '$amount'},
                    'count': {'$sum': 1}
                }
            },
            {'$sort': {'total': -1}}
        ]
        
        return list(db.transactions.aggregate(pipeline))
    except Exception as e:
        print(f"Erro em get_expenses_by_category_period: {e}")
        return []

def get_period_transactions(owner_id, owner_type, start_date, end_date):
    try:
        from app import get_db
        from bson.objectid import ObjectId
        
        db = get_db()
        transactions = db.transactions.find({
            'owner_id': ObjectId(owner_id),
            'owner_type': owner_type,
            'date': {'$gte': start_date, '$lt': end_date}
        }).sort('date', -1)
        
        return list(transactions)
    except Exception as e:
        print(f"Erro em get_period_transactions: {e}")
        return []