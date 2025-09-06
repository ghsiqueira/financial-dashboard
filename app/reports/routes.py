from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, make_response
from app.auth.routes import login_required
from app.models import User, Transaction
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import calendar
import json
import csv
import io

reports = Blueprint('reports', __name__)

@reports.route('/generate', methods=['POST'])
@login_required
def generate_report():
    """Gerar relatório personalizado"""
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        data = request.get_json() if request.is_json else request.form
        
        # Parâmetros do relatório
        report_type = data.get('type', 'summary')  # summary, detailed, comparison
        start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d')
        categories = data.get('categories', [])  # Lista de categorias específicas
        
        # Determinar conta
        account_type = data.get('account', 'individual')
        if account_type == 'family' and user.default_family:
            owner_type = 'family'
            owner_id = user.default_family
        else:
            owner_type = 'individual'
            owner_id = user_id
        
        # Gerar relatório baseado no tipo
        if report_type == 'summary':
            report_data = generate_summary_report(owner_id, owner_type, start_date, end_date)
        elif report_type == 'detailed':
            report_data = generate_detailed_report(owner_id, owner_type, start_date, end_date, categories)
        elif report_type == 'comparison':
            report_data = generate_comparison_report(owner_id, owner_type, start_date, end_date)
        else:
            raise ValueError('Tipo de relatório inválido')
        
        return jsonify({
            'success': True,
            'report': report_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@reports.route('/export/<format>')
@login_required
def export_report(format):
    """Exportar relatório em diferentes formatos"""
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        # Parâmetros da query
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        account = request.args.get('account', 'individual')
        
        if not start_date or not end_date:
            start_date = datetime.now().replace(day=1)
            end_date = datetime.now()
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Determinar conta
        if account == 'family' and user.default_family:
            owner_type = 'family'
            owner_id = user.default_family
        else:
            owner_type = 'individual'
            owner_id = user_id
        
        if format.lower() == 'csv':
            return export_csv_report(owner_id, owner_type, start_date, end_date)
        elif format.lower() == 'json':
            return export_json_report(owner_id, owner_type, start_date, end_date)
        else:
            return jsonify({'error': 'Formato não suportado'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports.route('/api/insights/<owner_id>')
@login_required
def api_financial_insights(owner_id):
    """Gerar insights financeiros inteligentes"""
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        # Verificar acesso
        if owner_id != user_id and (not user.default_family or str(user.default_family) != owner_id):
            return jsonify({'error': 'Sem acesso'}), 403
        
        owner_type = 'individual' if owner_id == user_id else 'family'
        
        insights = generate_financial_insights(owner_id, owner_type)
        
        return jsonify(insights)
        
    except Exception as e:
        return jsonify({'error': 'Erro ao gerar insights'}), 500

@reports.route('/api/trends/<owner_id>')
@login_required
def api_spending_trends(owner_id):
    """Análise de tendências de gastos"""
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        # Verificar acesso
        if owner_id != user_id and (not user.default_family or str(user.default_family) != owner_id):
            return jsonify({'error': 'Sem acesso'}), 403
        
        owner_type = 'individual' if owner_id == user_id else 'family'
        period = request.args.get('period', '6months')  # 3months, 6months, 1year
        
        trends = analyze_spending_trends(owner_id, owner_type, period)
        
        return jsonify(trends)
        
    except Exception as e:
        return jsonify({'error': 'Erro ao analisar tendências'}), 500

@reports.route('/api/forecast/<owner_id>')
@login_required
def api_financial_forecast(owner_id):
    """Previsão financeira baseada em dados históricos"""
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        # Verificar acesso
        if owner_id != user_id and (not user.default_family or str(user.default_family) != owner_id):
            return jsonify({'error': 'Sem acesso'}), 403
        
        owner_type = 'individual' if owner_id == user_id else 'family'
        months_ahead = int(request.args.get('months', 3))
        
        forecast = generate_financial_forecast(owner_id, owner_type, months_ahead)
        
        return jsonify(forecast)
        
    except Exception as e:
        return jsonify({'error': 'Erro ao gerar previsão'}), 500

# Funções auxiliares para geração de relatórios

def generate_summary_report(owner_id, owner_type, start_date, end_date):
    """Relatório resumo do período"""
    from app import get_db
    db = get_db()
    
    # Resumo geral
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
                '_id': '$type',
                'total': {'$sum': '$amount'},
                'count': {'$sum': 1},
                'avg': {'$avg': '$amount'}
            }
        }
    ]
    
    result = list(db.transactions.aggregate(pipeline))
    
    summary = {'income': 0, 'expense': 0, 'balance': 0, 'total_transactions': 0}
    
    for item in result:
        summary[item['_id']] = item['total']
        summary['total_transactions'] += item['count']
    
    summary['balance'] = summary['income'] - summary['expense']
    
    # Gastos por categoria
    category_pipeline = [
        {
            '$match': {
                'owner_id': ObjectId(owner_id),
                'owner_type': owner_type,
                'type': 'expense',
                'date': {'$gte': start_date, '$lte': end_date}
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
    
    categories = list(db.transactions.aggregate(category_pipeline))
    
    return {
        'period': f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}",
        'summary': summary,
        'categories': categories,
        'days': (end_date - start_date).days + 1
    }

def generate_detailed_report(owner_id, owner_type, start_date, end_date, categories=None):
    """Relatório detalhado com transações"""
    from app import get_db
    db = get_db()
    
    # Filtro base
    match_filter = {
        'owner_id': ObjectId(owner_id),
        'owner_type': owner_type,
        'date': {'$gte': start_date, '$lte': end_date}
    }
    
    # Filtrar por categorias se especificado
    if categories:
        match_filter['category'] = {'$in': categories}
    
    # Buscar transações
    transactions = list(db.transactions.find(match_filter).sort('date', -1))
    
    # Converter ObjectIds para strings
    for transaction in transactions:
        transaction['_id'] = str(transaction['_id'])
        transaction['owner_id'] = str(transaction['owner_id'])
        transaction['added_by'] = str(transaction['added_by'])
        transaction['date'] = transaction['date'].isoformat()
    
    # Estatísticas por dia
    daily_stats = {}
    for transaction in transactions:
        date_key = transaction['date'][:10]  # YYYY-MM-DD
        if date_key not in daily_stats:
            daily_stats[date_key] = {'income': 0, 'expense': 0, 'count': 0}
        
        daily_stats[date_key][transaction['type']] += transaction['amount']
        daily_stats[date_key]['count'] += 1
    
    return {
        'transactions': transactions,
        'daily_stats': daily_stats,
        'total_transactions': len(transactions)
    }

def generate_comparison_report(owner_id, owner_type, start_date, end_date):
    """Relatório comparativo com período anterior"""
    # Período atual
    current_report = generate_summary_report(owner_id, owner_type, start_date, end_date)
    
    # Período anterior (mesmo número de dias)
    days_diff = (end_date - start_date).days
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days_diff)
    
    previous_report = generate_summary_report(owner_id, owner_type, prev_start, prev_end)
    
    # Calcular variações
    def calculate_variation(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return ((current - previous) / previous) * 100
    
    variations = {
        'income': calculate_variation(current_report['summary']['income'], previous_report['summary']['income']),
        'expense': calculate_variation(current_report['summary']['expense'], previous_report['summary']['expense']),
        'balance': calculate_variation(current_report['summary']['balance'], previous_report['summary']['balance'])
    }
    
    return {
        'current': current_report,
        'previous': previous_report,
        'variations': variations
    }

def generate_financial_insights(owner_id, owner_type):
    """Gerar insights financeiros inteligentes"""
    from app import get_db
    db = get_db()
    
    # Últimos 6 meses de dados
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    insights = []
    
    # 1. Categoria com maior crescimento
    monthly_categories = get_monthly_category_spending(db, owner_id, owner_type, start_date, end_date)
    
    if monthly_categories:
        growth_analysis = analyze_category_growth(monthly_categories)
        if growth_analysis:
            insights.append({
                'type': 'warning',
                'title': 'Categoria em Crescimento',
                'message': f"Seus gastos com {growth_analysis['category']} aumentaram {growth_analysis['growth']:.1f}% nos últimos meses",
                'category': growth_analysis['category'],
                'data': growth_analysis
            })
    
    # 2. Melhor mês de economia
    monthly_balance = get_monthly_balance(db, owner_id, owner_type, start_date, end_date)
    if monthly_balance:
        best_month = max(monthly_balance, key=lambda x: x['balance'])
        insights.append({
            'type': 'success',
            'title': 'Melhor Mês',
            'message': f"Seu melhor mês foi {best_month['month']}/{best_month['year']} com saldo de R$ {best_month['balance']:.2f}",
            'data': best_month
        })
    
    # 3. Padrão de gastos
    spending_pattern = analyze_spending_pattern(db, owner_id, owner_type)
    if spending_pattern:
        insights.append({
            'type': 'info',
            'title': 'Padrão de Gastos',
            'message': spending_pattern['message'],
            'data': spending_pattern
        })
    
    return insights

def analyze_spending_trends(owner_id, owner_type, period):
    """Analisar tendências de gastos"""
    from app import get_db
    db = get_db()
    
    # Definir período
    end_date = datetime.now()
    if period == '3months':
        start_date = end_date - timedelta(days=90)
        months = 3
    elif period == '1year':
        start_date = end_date - timedelta(days=365)
        months = 12
    else:  # 6months
        start_date = end_date - timedelta(days=180)
        months = 6
    
    # Gastos mensais por categoria
    pipeline = [
        {
            '$match': {
                'owner_id': ObjectId(owner_id),
                'owner_type': owner_type,
                'type': 'expense',
                'date': {'$gte': start_date, '$lte': end_date}
            }
        },
        {
            '$group': {
                '_id': {
                    'year': {'$year': '$date'},
                    'month': {'$month': '$date'},
                    'category': '$category'
                },
                'total': {'$sum': '$amount'}
            }
        },
        {'$sort': {'_id.year': 1, '_id.month': 1}}
    ]
    
    result = list(db.transactions.aggregate(pipeline))
    
    # Organizar dados por categoria
    trends = {}
    for item in result:
        category = item['_id']['category']
        month_key = f"{item['_id']['year']}-{item['_id']['month']:02d}"
        
        if category not in trends:
            trends[category] = {}
        
        trends[category][month_key] = item['total']
    
    # Calcular tendências (crescimento/decrescimento)
    trend_analysis = {}
    for category, monthly_data in trends.items():
        values = list(monthly_data.values())
        if len(values) >= 2:
            # Regressão linear simples para detectar tendência
            trend = calculate_trend(values)
            trend_analysis[category] = {
                'trend': trend,
                'monthly_data': monthly_data,
                'total': sum(values),
                'average': sum(values) / len(values)
            }
    
    return trend_analysis

def generate_financial_forecast(owner_id, owner_type, months_ahead):
    """Gerar previsão financeira baseada em dados históricos"""
    from app import get_db
    db = get_db()
    
    # Últimos 12 meses para base de cálculo
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # Dados mensais históricos
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
    
    # Organizar dados históricos
    monthly_data = {}
    for item in result:
        month_key = f"{item['_id']['year']}-{item['_id']['month']:02d}"
        if month_key not in monthly_data:
            monthly_data[month_key] = {'income': 0, 'expense': 0}
        monthly_data[month_key][item['_id']['type']] = item['total']
    
    # Calcular médias e tendências
    income_values = [data['income'] for data in monthly_data.values()]
    expense_values = [data['expense'] for data in monthly_data.values()]
    
    avg_income = sum(income_values) / len(income_values) if income_values else 0
    avg_expense = sum(expense_values) / len(expense_values) if expense_values else 0
    
    # Tendência simples (média dos últimos 3 meses vs média geral)
    recent_income = sum(income_values[-3:]) / 3 if len(income_values) >= 3 else avg_income
    recent_expense = sum(expense_values[-3:]) / 3 if len(expense_values) >= 3 else avg_expense
    
    income_trend = (recent_income - avg_income) / avg_income if avg_income > 0 else 0
    expense_trend = (recent_expense - avg_expense) / avg_expense if avg_expense > 0 else 0
    
    # Gerar previsão para os próximos meses
    forecast = []
    current_income = recent_income
    current_expense = recent_expense
    
    for i in range(months_ahead):
        # Aplicar tendência gradualmente (suavizada)
        current_income *= (1 + income_trend * 0.1)  # 10% da tendência por mês
        current_expense *= (1 + expense_trend * 0.1)
        
        forecast_date = end_date + timedelta(days=30 * (i + 1))
        forecast.append({
            'month': forecast_date.strftime('%m/%Y'),
            'predicted_income': round(current_income, 2),
            'predicted_expense': round(current_expense, 2),
            'predicted_balance': round(current_income - current_expense, 2)
        })
    
    return {
        'historical_average': {
            'income': round(avg_income, 2),
            'expense': round(avg_expense, 2),
            'balance': round(avg_income - avg_expense, 2)
        },
        'trends': {
            'income_trend': round(income_trend * 100, 2),  # Percentual
            'expense_trend': round(expense_trend * 100, 2)
        },
        'forecast': forecast
    }

def export_csv_report(owner_id, owner_type, start_date, end_date):
    """Exportar relatório em formato CSV"""
    from app import get_db
    db = get_db()
    
    # Buscar transações do período
    transactions = db.transactions.find({
        'owner_id': ObjectId(owner_id),
        'owner_type': owner_type,
        'date': {'$gte': start_date, '$lte': end_date}
    }).sort('date', -1)
    
    # Criar CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Cabeçalho
    writer.writerow([
        'Data', 'Tipo', 'Categoria', 'Descrição', 'Valor', 
        'Método de Pagamento', 'Tags', 'Adicionado por'
    ])
    
    # Dados
    for transaction in transactions:
        # Buscar nome do usuário que adicionou
        user = User.find_by_id(transaction['added_by'])
        added_by_name = user.name if user else 'Usuário não encontrado'
        
        writer.writerow([
            transaction['date'].strftime('%d/%m/%Y %H:%M'),
            'Receita' if transaction['type'] == 'income' else 'Despesa',
            transaction['category'],
            transaction.get('description', ''),
            f"{transaction['amount']:.2f}".replace('.', ','),
            transaction.get('payment_method', ''),
            ', '.join(transaction.get('tags', [])),
            added_by_name
        ])
    
    # Criar resposta
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=relatorio_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.csv'
    
    return response

def export_json_report(owner_id, owner_type, start_date, end_date):
    """Exportar relatório em formato JSON"""
    report_data = generate_detailed_report(owner_id, owner_type, start_date, end_date)
    
    response = make_response(json.dumps(report_data, indent=2, ensure_ascii=False))
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=relatorio_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.json'
    
    return response

# Funções auxiliares para análises

def get_monthly_category_spending(db, owner_id, owner_type, start_date, end_date):
    """Obter gastos mensais por categoria"""
    pipeline = [
        {
            '$match': {
                'owner_id': ObjectId(owner_id),
                'owner_type': owner_type,
                'type': 'expense',
                'date': {'$gte': start_date, '$lte': end_date}
            }
        },
        {
            '$group': {
                '_id': {
                    'year': {'$year': '$date'},
                    'month': {'$month': '$date'},
                    'category': '$category'
                },
                'total': {'$sum': '$amount'}
            }
        },
        {'$sort': {'_id.year': 1, '_id.month': 1}}
    ]
    
    return list(db.transactions.aggregate(pipeline))

def analyze_category_growth(monthly_data):
    """Analisar crescimento por categoria"""
    categories = {}
    
    # Organizar dados por categoria
    for item in monthly_data:
        category = item['_id']['category']
        month_key = f"{item['_id']['year']}-{item['_id']['month']:02d}"
        
        if category not in categories:
            categories[category] = []
        
        categories[category].append(item['total'])
    
    # Encontrar categoria com maior crescimento
    max_growth = 0
    growing_category = None
    
    for category, values in categories.items():
        if len(values) >= 2:
            # Comparar últimos 2 valores
            recent_avg = sum(values[-2:]) / 2
            older_avg = sum(values[:-2]) / len(values[:-2]) if len(values) > 2 else values[0]
            
            if older_avg > 0:
                growth = ((recent_avg - older_avg) / older_avg) * 100
                if growth > max_growth:
                    max_growth = growth
                    growing_category = category
    
    if growing_category and max_growth > 10:  # Só alertar se crescimento > 10%
        return {
            'category': growing_category,
            'growth': max_growth
        }
    
    return None

def get_monthly_balance(db, owner_id, owner_type, start_date, end_date):
    """Obter saldo mensal"""
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
    
    # Calcular saldo mensal
    monthly_balance = {}
    for item in result:
        month_key = f"{item['_id']['year']}-{item['_id']['month']:02d}"
        if month_key not in monthly_balance:
            monthly_balance[month_key] = {'income': 0, 'expense': 0, 'year': item['_id']['year'], 'month': item['_id']['month']}
        
        monthly_balance[month_key][item['_id']['type']] = item['total']
    
    # Calcular balance
    for data in monthly_balance.values():
        data['balance'] = data['income'] - data['expense']
    
    return list(monthly_balance.values())

def analyze_spending_pattern(db, owner_id, owner_type):
    """Analisar padrão de gastos (dia da semana, hora, etc.)"""
    pipeline = [
        {
            '$match': {
                'owner_id': ObjectId(owner_id),
                'owner_type': owner_type,
                'type': 'expense',
                'date': {'$gte': datetime.now() - timedelta(days=90)}
            }
        },
        {
            '$group': {
                '_id': {'$dayOfWeek': '$date'},
                'total': {'$sum': '$amount'},
                'count': {'$sum': 1}
            }
        },
        {'$sort': {'total': -1}}
    ]
    
    result = list(db.transactions.aggregate(pipeline))
    
    if result:
        # Dia da semana com mais gastos (1=Domingo, 7=Sábado)
        days = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
        top_day = result[0]
        day_name = days[top_day['_id'] - 1]
        
        return {
            'message': f"Você gasta mais às {day_name}s (R$ {top_day['total']:.2f} em média)",
            'top_day': day_name,
            'amount': top_day['total']
        }
    
    return None

def calculate_trend(values):
    """Calcular tendência simples usando regressão linear básica"""
    if len(values) < 2:
        return 0
    
    n = len(values)
    x_sum = sum(range(n))
    y_sum = sum(values)
    xy_sum = sum(i * values[i] for i in range(n))
    x2_sum = sum(i * i for i in range(n))
    
    # Coeficiente angular da regressão linear
    slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
    
    return slope