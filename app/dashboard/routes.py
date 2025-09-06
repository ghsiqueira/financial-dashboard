from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from app.auth.routes import login_required
from app.models import User, Transaction, Budget, Family
from app.dashboard.charts import generate_charts_data
from datetime import datetime, timedelta
import calendar

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/overview')
@login_required
def overview():
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    # Determinar conta ativa (individual ou família)
    active_account = request.args.get('account', 'individual')
    active_family_id = None
    
    if active_account == 'family' and user.default_family:
        active_family_id = user.default_family
        owner_type = 'family'
        owner_id = active_family_id
    else:
        owner_type = 'individual'
        owner_id = user_id
    
    # Resumo do mês atual
    monthly_summary = Transaction.get_monthly_summary(owner_id, owner_type)
    
    # Transações recentes
    recent_transactions = Transaction.get_user_transactions(
        user_id, owner_type, owner_id, limit=10
    )
    
    # Dados para gráficos
    charts_data = generate_charts_data(owner_id, owner_type)
    
    # Orçamentos
    budgets = get_user_budgets(owner_id, owner_type)
    
    # Famílias do usuário
    user_families = []
    if user.families:
        for family_id in user.families:
            family = Family.find_by_id(family_id)
            if family:
                user_families.append(family)
    
    context = {
        'user': user,
        'monthly_summary': monthly_summary,
        'recent_transactions': recent_transactions,
        'charts_data': charts_data,
        'budgets': budgets,
        'user_families': user_families,
        'active_account': active_account,
        'active_family_id': str(active_family_id) if active_family_id else None
    }
    
    return render_template('dashboard/overview.html', **context)

@dashboard.route('/transactions')
@login_required
def transactions():
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
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
    
    # Buscar transações com filtros
    transactions = get_filtered_transactions(
        owner_id, owner_type, page, limit, category, 
        transaction_type, date_from, date_to
    )
    
    # Categorias para filtro
    categories = get_categories(owner_id, owner_type)
    
    context = {
        'user': user,
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

@dashboard.route('/budgets')
@login_required
def budgets():
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    # Conta ativa
    active_account = request.args.get('account', 'individual')
    if active_account == 'family' and user.default_family:
        owner_type = 'family'
        owner_id = user.default_family
    else:
        owner_type = 'individual'
        owner_id = user_id
    
    # Orçamentos
    budgets = get_user_budgets(owner_id, owner_type)
    
    # Atualizar valores gastos
    for budget in budgets:
        budget_obj = Budget(owner_id, owner_type, budget['category'], budget['limit'])
        budget_obj._id = budget['_id']
        budget_obj.update_spent_amount()
        budget['current_spent'] = budget_obj.current_spent
        budget['percentage'] = (budget['current_spent'] / budget['limit']) * 100
        budget['remaining'] = budget['limit'] - budget['current_spent']
    
    context = {
        'user': user,
        'budgets': budgets,
        'active_account': active_account
    }
    
    return render_template('dashboard/budgets.html', **context)

@dashboard.route('/reports')
@login_required
def reports():
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
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
    
    if month:
        month = int(month)
        report_data = generate_monthly_report(owner_id, owner_type, year, month)
        report_type = 'monthly'
    else:
        report_data = generate_yearly_report(owner_id, owner_type, year)
        report_type = 'yearly'
    
    context = {
        'user': user,
        'report_data': report_data,
        'report_type': report_type,
        'year': year,
        'month': month,
        'active_account': active_account
    }
    
    return render_template('dashboard/reports.html', **context)

# API endpoints
@dashboard.route('/api/summary')
@login_required
def api_summary():
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

@dashboard.route('/api/charts/<chart_type>')
@login_required
def api_charts(chart_type):
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

# Funções auxiliares
def get_user_budgets(owner_id, owner_type):
    from app import get_db
    from bson.objectid import ObjectId
    
    db = get_db()
    budgets = db.budgets.find({
        'owner_id': ObjectId(owner_id),
        'owner_type': owner_type
    })
    return list(budgets)

def get_filtered_transactions(owner_id, owner_type, page, limit, category, 
                            transaction_type, date_from, date_to):
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

def get_categories(owner_id, owner_type):
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

def get_expenses_by_category(owner_id, owner_type):
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

def get_monthly_evolution(owner_id, owner_type):
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
    current = start_date
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

def get_income_vs_expenses(owner_id, owner_type):
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

def generate_monthly_report(owner_id, owner_type, year, month):
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

def generate_yearly_report(owner_id, owner_type, year):
    from app import get_db
    from bson.objectid import ObjectId
    
    db = get_db()
    start_date = datetime(year, 1, 1)
    end_date = datetime(year + 1, 1, 1)
    
    # Resumo por mês
    monthly_summaries = []
    for month in range(1, 13):
        summary = Transaction.get_monthly_summary(owner_id, owner_type, year, month)
        summary['month'] = calendar.month_name[month]
        monthly_summaries.append(summary)
    
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

def get_expenses_by_category_period(owner_id, owner_type, start_date, end_date):
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

def get_period_transactions(owner_id, owner_type, start_date, end_date):
    from app import get_db
    from bson.objectid import ObjectId
    
    db = get_db()
    transactions = db.transactions.find({
        'owner_id': ObjectId(owner_id),
        'owner_type': owner_type,
        'date': {'$gte': start_date, '$lt': end_date}
    }).sort('date', -1)
    
    return list(transactions)