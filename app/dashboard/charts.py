import plotly.graph_objs as go
import plotly.utils
from datetime import datetime, timedelta
from app import get_db
from bson.objectid import ObjectId
import json

def generate_charts_data(owner_id, owner_type):
    """Gera todos os dados dos gráficos para o dashboard"""
    
    charts = {
        'expenses_pie': generate_expenses_pie_chart(owner_id, owner_type),
        'monthly_evolution': generate_monthly_evolution_chart(owner_id, owner_type),
        'income_vs_expenses': generate_income_vs_expenses_chart(owner_id, owner_type),
        'category_trends': generate_category_trends_chart(owner_id, owner_type),
        'daily_spending': generate_daily_spending_chart(owner_id, owner_type)
    }
    
    return charts

def generate_expenses_pie_chart(owner_id, owner_type):
    """Gráfico de pizza dos gastos por categoria (últimos 30 dias)"""
    
    db = get_db()
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
                'total': {'$sum': '$amount'}
            }
        },
        {'$sort': {'total': -1}},
        {'$limit': 10}  # Top 10 categorias
    ]
    
    result = list(db.transactions.aggregate(pipeline))
    
    if not result:
        return None
    
    labels = [item['_id'] or 'Sem categoria' for item in result]
    values = [item['total'] for item in result]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hovertemplate='<b>%{label}</b><br>' +
                      'Valor: R$ %{value:,.2f}<br>' +
                      'Percentual: %{percent}<br>' +
                      '<extra></extra>',
        textinfo='label+percent',
        hole=0.3
    )])
    
    fig.update_layout(
        title='Gastos por Categoria (Últimos 30 dias)',
        showlegend=True,
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def generate_monthly_evolution_chart(owner_id, owner_type):
    """Gráfico de evolução mensal receitas vs despesas"""
    
    db = get_db()
    # Últimos 12 meses
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    pipeline = [
        {
            '$match': {
                'owner_id': ObjectId(owner_id),
                'owner_type': owner_type,
                'date': {'$gte': start_date}
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
    
    # Organizar dados
    months = []
    income_data = []
    expense_data = []
    balance_data = []
    
    # Gerar últimos 12 meses
    current_date = datetime.now().replace(day=1)
    for i in range(12):
        month_date = current_date - timedelta(days=30 * i)
        month_key = f"{month_date.strftime('%b')} {month_date.year}"
        months.insert(0, month_key)
        
        # Buscar dados do mês
        month_income = 0
        month_expense = 0
        
        for item in result:
            if (item['_id']['year'] == month_date.year and 
                item['_id']['month'] == month_date.month):
                if item['_id']['type'] == 'income':
                    month_income = item['total']
                elif item['_id']['type'] == 'expense':
                    month_expense = item['total']
        
        income_data.insert(0, month_income)
        expense_data.insert(0, month_expense)
        balance_data.insert(0, month_income - month_expense)
    
    fig = go.Figure()
    
    # Receitas
    fig.add_trace(go.Scatter(
        x=months,
        y=income_data,
        mode='lines+markers',
        name='Receitas',
        line=dict(color='#28a745', width=3),
        marker=dict(size=8),
        hovertemplate='<b>Receitas</b><br>' +
                      'Mês: %{x}<br>' +
                      'Valor: R$ %{y:,.2f}<br>' +
                      '<extra></extra>'
    ))
    
    # Despesas
    fig.add_trace(go.Scatter(
        x=months,
        y=expense_data,
        mode='lines+markers',
        name='Despesas',
        line=dict(color='#dc3545', width=3),
        marker=dict(size=8),
        hovertemplate='<b>Despesas</b><br>' +
                      'Mês: %{x}<br>' +
                      'Valor: R$ %{y:,.2f}<br>' +
                      '<extra></extra>'
    ))
    
    # Saldo
    fig.add_trace(go.Scatter(
        x=months,
        y=balance_data,
        mode='lines+markers',
        name='Saldo',
        line=dict(color='#17a2b8', width=2, dash='dash'),
        marker=dict(size=6),
        hovertemplate='<b>Saldo</b><br>' +
                      'Mês: %{x}<br>' +
                      'Valor: R$ %{y:,.2f}<br>' +
                      '<extra></extra>'
    ))
    
    fig.update_layout(
        title='Evolução Financeira (Últimos 12 meses)',
        xaxis_title='Mês',
        yaxis_title='Valor (R$)',
        hovermode='x unified',
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def generate_income_vs_expenses_chart(owner_id, owner_type):
    """Gráfico de barras comparando receitas vs despesas mensais"""
    
    db = get_db()
    # Últimos 6 meses
    months_data = []
    
    for i in range(6):
        date = datetime.now().replace(day=1) - timedelta(days=30 * i)
        year = date.year
        month = date.month
        
        summary = get_month_summary(owner_id, owner_type, year, month)
        
        months_data.insert(0, {
            'month': date.strftime('%b %Y'),
            'income': summary['income'],
            'expense': summary['expense']
        })
    
    months = [item['month'] for item in months_data]
    income_values = [item['income'] for item in months_data]
    expense_values = [item['expense'] for item in months_data]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=months,
        y=income_values,
        name='Receitas',
        marker_color='#28a745',
        hovertemplate='<b>Receitas</b><br>' +
                      'Mês: %{x}<br>' +
                      'Valor: R$ %{y:,.2f}<br>' +
                      '<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        x=months,
        y=expense_values,
        name='Despesas',
        marker_color='#dc3545',
        hovertemplate='<b>Despesas</b><br>' +
                      'Mês: %{x}<br>' +
                      'Valor: R$ %{y:,.2f}<br>' +
                      '<extra></extra>'
    ))
    
    fig.update_layout(
        title='Receitas vs Despesas (Últimos 6 meses)',
        xaxis_title='Mês',
        yaxis_title='Valor (R$)',
        barmode='group',
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def generate_category_trends_chart(owner_id, owner_type):
    """Gráfico de tendências das principais categorias"""
    
    db = get_db()
    # Buscar top 5 categorias dos últimos 3 meses
    start_date = datetime.now() - timedelta(days=90)
    
    top_categories_pipeline = [
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
                'total': {'$sum': '$amount'}
            }
        },
        {'$sort': {'total': -1}},
        {'$limit': 5}
    ]
    
    top_categories = list(db.transactions.aggregate(top_categories_pipeline))
    
    if not top_categories:
        return None
    
    fig = go.Figure()
    
    # Para cada categoria, buscar evolução mensal
    for category_data in top_categories:
        category = category_data['_id']
        monthly_values = []
        months = []
        
        for i in range(6):  # Últimos 6 meses
            date = datetime.now().replace(day=1) - timedelta(days=30 * i)
            start_month = date
            end_month = (date.replace(day=28) + timedelta(days=4)).replace(day=1)
            
            month_total = get_category_month_total(
                owner_id, owner_type, category, start_month, end_month
            )
            
            monthly_values.insert(0, month_total)
            months.insert(0, date.strftime('%b'))
        
        fig.add_trace(go.Scatter(
            x=months,
            y=monthly_values,
            mode='lines+markers',
            name=category or 'Sem categoria',
            line=dict(width=2),
            marker=dict(size=6),
            hovertemplate=f'<b>{category}</b><br>' +
                          'Mês: %{x}<br>' +
                          'Valor: R$ %{y:,.2f}<br>' +
                          '<extra></extra>'
        ))
    
    fig.update_layout(
        title='Tendência das Principais Categorias',
        xaxis_title='Mês',
        yaxis_title='Valor (R$)',
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def generate_daily_spending_chart(owner_id, owner_type):
    """Gráfico de gastos diários do mês atual"""
    
    db = get_db()
    now = datetime.now()
    start_month = now.replace(day=1)
    
    pipeline = [
        {
            '$match': {
                'owner_id': ObjectId(owner_id),
                'owner_type': owner_type,
                'type': 'expense',
                'date': {'$gte': start_month}
            }
        },
        {
            '$group': {
                '_id': {'$dayOfMonth': '$date'},
                'total': {'$sum': '$amount'}
            }
        },
        {'$sort': {'_id': 1}}
    ]
    
    result = list(db.transactions.aggregate(pipeline))
    
    # Criar array com todos os dias do mês
    days_in_month = (now.replace(month=now.month+1, day=1) - timedelta(days=1)).day if now.month < 12 else 31
    daily_data = [0] * days_in_month
    
    for item in result:
        day = item['_id']
        if 1 <= day <= days_in_month:
            daily_data[day - 1] = item['total']
    
    days = list(range(1, days_in_month + 1))
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=days,
        y=daily_data,
        name='Gastos Diários',
        marker_color='#17a2b8',
        hovertemplate='<b>Dia %{x}</b><br>' +
                      'Gastos: R$ %{y:,.2f}<br>' +
                      '<extra></extra>'
    ))
    
    # Adicionar linha da média
    if daily_data:
        avg_spending = sum(daily_data) / len([x for x in daily_data if x > 0])
        fig.add_hline(
            y=avg_spending,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Média: R$ {avg_spending:,.2f}"
        )
    
    fig.update_layout(
        title=f'Gastos Diários - {now.strftime("%B %Y")}',
        xaxis_title='Dia do Mês',
        yaxis_title='Valor (R$)',
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

# Funções auxiliares
def get_month_summary(owner_id, owner_type, year, month):
    """Resumo financeiro de um mês específico"""
    from app.models import Transaction
    return Transaction.get_monthly_summary(owner_id, owner_type, year, month)

def get_category_month_total(owner_id, owner_type, category, start_date, end_date):
    """Total gasto em uma categoria em um período"""
    
    db = get_db()
    pipeline = [
        {
            '$match': {
                'owner_id': ObjectId(owner_id),
                'owner_type': owner_type,
                'category': category,
                'type': 'expense',
                'date': {'$gte': start_date, '$lt': end_date}
            }
        },
        {
            '$group': {
                '_id': None,
                'total': {'$sum': '$amount'}
            }
        }
    ]
    
    result = list(db.transactions.aggregate(pipeline))
    return result[0]['total'] if result else 0