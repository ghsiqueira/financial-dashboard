from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from app.auth.routes import login_required
from app.models import User
from bson.objectid import ObjectId
from datetime import datetime, timedelta

notifications = Blueprint('notifications', __name__)

@notifications.route('/center')
@login_required
def center():
    """Central de notificações - página principal"""
    user = User.find_by_id(session['user_id'])
    return render_template('notifications/center.html', user=user)

@notifications.route('/api/user/<user_id>')
@login_required
def api_user_notifications(user_id):
    """Obter todas as notificações do usuário"""
    try:
        # Verificar se é o próprio usuário
        if session['user_id'] != user_id:
            return jsonify({'error': 'Sem permissão'}), 403
        
        user = User.find_by_id(user_id)
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        notifications_list = []
        
        # 1. Alertas de orçamento
        budget_alerts = get_budget_alerts(user_id, user)
        notifications_list.extend(budget_alerts)
        
        # 2. Convites de família pendentes
        family_invites = get_family_invites(user_id)
        notifications_list.extend(family_invites)
        
        # 3. Insights financeiros
        financial_insights = get_financial_insights_notifications(user_id, user)
        notifications_list.extend(financial_insights)
        
        # 4. Lembretes de transações
        transaction_reminders = get_transaction_reminders(user_id, user)
        notifications_list.extend(transaction_reminders)
        
        # Ordenar por prioridade e data
        notifications_list.sort(key=lambda x: (x['priority'], x['created_at']), reverse=True)
        
        return jsonify({
            'notifications': notifications_list,
            'unread_count': len([n for n in notifications_list if not n.get('read', False)])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications.route('/api/mark_read', methods=['POST'])
@login_required
def mark_notification_read():
    """Marcar notificação como lida"""
    try:
        data = request.get_json()
        notification_id = data.get('notification_id')
        user_id = session['user_id']
        
        if not notification_id:
            return jsonify({'error': 'ID da notificação obrigatório'}), 400
        
        # Marcar como lida no banco (implementar conforme estrutura de dados)
        from app import get_db
        db = get_db()
        
        db.notifications.update_one(
            {
                '_id': ObjectId(notification_id),
                'user_id': ObjectId(user_id)
            },
            {'$set': {'read': True, 'read_at': datetime.utcnow()}}
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications.route('/api/mark_all_read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Marcar todas as notificações como lidas"""
    try:
        user_id = session['user_id']
        
        from app import get_db
        db = get_db()
        
        db.notifications.update_many(
            {'user_id': ObjectId(user_id), 'read': {'$ne': True}},
            {'$set': {'read': True, 'read_at': datetime.utcnow()}}
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@notifications.route('/api/settings/<user_id>', methods=['GET', 'POST'])
@login_required
def notification_settings(user_id):
    """Gerenciar configurações de notificação"""
    try:
        if session['user_id'] != user_id:
            return jsonify({'error': 'Sem permissão'}), 403
        
        from app import get_db
        db = get_db()
        
        if request.method == 'POST':
            data = request.get_json()
            
            settings = {
                'budget_alerts': data.get('budget_alerts', True),
                'family_invites': data.get('family_invites', True),
                'financial_insights': data.get('financial_insights', True),
                'transaction_reminders': data.get('transaction_reminders', True),
                'email_notifications': data.get('email_notifications', False),
                'push_notifications': data.get('push_notifications', True)
            }
            
            # Atualizar configurações do usuário
            db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'notification_settings': settings}}
            )
            
            return jsonify({'success': True, 'settings': settings})
        
        else:
            # GET - obter configurações atuais
            user_data = db.users.find_one({'_id': ObjectId(user_id)})
            settings = user_data.get('notification_settings', {
                'budget_alerts': True,
                'family_invites': True,
                'financial_insights': True,
                'transaction_reminders': True,
                'email_notifications': False,
                'push_notifications': True
            })
            
            return jsonify({'settings': settings})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Funções auxiliares para diferentes tipos de notificações

def get_budget_alerts(user_id, user):
    """Obter alertas de orçamento"""
    from app import get_db
    db = get_db()
    
    alerts = []
    
    # Verificar orçamentos individuais
    individual_budgets = db.budgets.find({
        'owner_id': ObjectId(user_id),
        'owner_type': 'individual',
        'alerts_enabled': True
    })
    
    for budget in individual_budgets:
        alert = check_budget_alert(budget)
        if alert:
            alerts.append(alert)
    
    # Verificar orçamentos familiares
    if hasattr(user, 'default_family') and user.default_family:
        family_budgets = db.budgets.find({
            'owner_id': user.default_family,
            'owner_type': 'family',
            'alerts_enabled': True
        })
        
        for budget in family_budgets:
            alert = check_budget_alert(budget, is_family=True)
            if alert:
                alerts.append(alert)
    
    return alerts

def check_budget_alert(budget, is_family=False):
    """Verificar se orçamento precisa de alerta"""
    from app.models import Budget
    
    # Calcular gasto atual
    budget_obj = Budget(
        budget['owner_id'],
        budget['owner_type'],
        budget['category'],
        budget['limit']
    )
    budget_obj._id = budget['_id']
    budget_obj.update_spent_amount()
    
    percentage = (budget_obj.current_spent / budget['limit'] * 100) if budget['limit'] > 0 else 0
    
    if percentage >= 100:
        return {
            'id': str(budget['_id']),
            'type': 'budget_exceeded',
            'priority': 1,  # Alta prioridade
            'title': 'Orçamento Excedido!',
            'message': f"Orçamento de {budget['category']} {'da família' if is_family else ''} foi excedido em {percentage-100:.1f}%",
            'category': budget['category'],
            'percentage': percentage,
            'is_family': is_family,
            'created_at': datetime.utcnow().isoformat(),
            'read': False
        }
    elif percentage >= 80:
        return {
            'id': str(budget['_id']),
            'type': 'budget_warning',
            'priority': 2,  # Média prioridade
            'title': 'Orçamento Quase Esgotado',
            'message': f"Orçamento de {budget['category']} {'da família' if is_family else ''} atingiu {percentage:.1f}%",
            'category': budget['category'],
            'percentage': percentage,
            'is_family': is_family,
            'created_at': datetime.utcnow().isoformat(),
            'read': False
        }
    
    return None

def get_family_invites(user_id):
    """Obter convites de família pendentes"""
    from app import get_db
    db = get_db()
    
    invites = db.invites.find({
        'invited_user_id': ObjectId(user_id),
        'status': 'pending',
        'expires_at': {'$gte': datetime.utcnow()}
    })
    
    notifications = []
    
    for invite in invites:
        # Buscar nome da família
        family = db.families.find_one({'_id': invite['family_id']})
        family_name = family['name'] if family else 'Família'
        
        # Buscar quem convidou
        inviter = User.find_by_id(invite['invited_by'])
        inviter_name = inviter.name if inviter else 'Alguém'
        
        notifications.append({
            'id': str(invite['_id']),
            'type': 'family_invite',
            'priority': 2,
            'title': 'Convite para Família',
            'message': f"{inviter_name} te convidou para {family_name}",
            'family_name': family_name,
            'inviter_name': inviter_name,
            'invite_code': invite['code'],
            'role': invite['role'],
            'created_at': invite['created_at'].isoformat(),
            'expires_at': invite['expires_at'].isoformat(),
            'read': False
        })
    
    return notifications

def get_financial_insights_notifications(user_id, user):
    """Obter insights financeiros como notificações"""
    notifications = []
    
    # Insight: Gastos crescentes
    spending_trend = analyze_recent_spending_trend(user_id, user)
    if spending_trend:
        notifications.append({
            'id': f"insight_spending_{user_id}",
            'type': 'financial_insight',
            'priority': 3,
            'title': 'Tendência de Gastos',
            'message': spending_trend['message'],
            'data': spending_trend,
            'created_at': datetime.utcnow().isoformat(),
            'read': False
        })
    
    # Insight: Oportunidade de economia
    savings_opportunity = find_savings_opportunity(user_id, user)
    if savings_opportunity:
        notifications.append({
            'id': f"insight_savings_{user_id}",
            'type': 'savings_opportunity',
            'priority': 3,
            'title': 'Oportunidade de Economia',
            'message': savings_opportunity['message'],
            'data': savings_opportunity,
            'created_at': datetime.utcnow().isoformat(),
            'read': False
        })
    
    return notifications

def get_transaction_reminders(user_id, user):
    """Obter lembretes de transações"""
    notifications = []
    
    # Lembrete: Transações recorrentes
    recurring_reminders = check_recurring_transactions(user_id)
    notifications.extend(recurring_reminders)
    
    # Lembrete: Muito tempo sem registrar transações
    inactivity_reminder = check_transaction_inactivity(user_id)
    if inactivity_reminder:
        notifications.append(inactivity_reminder)
    
    return notifications

def analyze_recent_spending_trend(user_id, user):
    """Analisar tendência de gastos recentes"""
    from app import get_db
    db = get_db()
    
    # Comparar este mês com o anterior
    now = datetime.now()
    current_month_start = now.replace(day=1)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    last_month_end = current_month_start - timedelta(days=1)
    
    # Gastos do mês atual
    current_expenses = db.transactions.aggregate([
        {
            '$match': {
                'added_by': ObjectId(user_id),
                'type': 'expense',
                'date': {'$gte': current_month_start}
            }
        },
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ])
    current_total = list(current_expenses)
    current_total = current_total[0]['total'] if current_total else 0
    
    # Gastos do mês anterior
    last_expenses = db.transactions.aggregate([
        {
            '$match': {
                'added_by': ObjectId(user_id),
                'type': 'expense',
                'date': {'$gte': last_month_start, '$lte': last_month_end}
            }
        },
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ])
    last_total = list(last_expenses)
    last_total = last_total[0]['total'] if last_total else 0
    
    # Calcular variação
    if last_total > 0:
        variation = ((current_total - last_total) / last_total) * 100
        
        if variation > 20:  # Aumento de mais de 20%
            return {
                'message': f"Seus gastos aumentaram {variation:.1f}% em relação ao mês passado",
                'variation': variation,
                'current_total': current_total,
                'last_total': last_total
            }
    
    return None

def find_savings_opportunity(user_id, user):
    """Encontrar oportunidades de economia"""
    from app import get_db
    db = get_db()
    
    # Última semana
    week_ago = datetime.now() - timedelta(days=7)
    
    # Categoria com mais gastos na semana
    weekly_expenses = db.transactions.aggregate([
        {
            '$match': {
                'added_by': ObjectId(user_id),
                'type': 'expense',
                'date': {'$gte': week_ago}
            }
        },
        {
            '$group': {
                '_id': '$category',
                'total': {'$sum': '$amount'},
                'count': {'$sum': 1}
            }
        },
        {'$sort': {'total': -1}},
        {'$limit': 1}
    ])
    
    top_category = list(weekly_expenses)
    if top_category and top_category[0]['total'] > 100:  # Mais de R$ 100 na semana
        category = top_category[0]
        return {
            'message': f"Você gastou R$ {category['total']:.2f} com {category['_id']} esta semana. Considere revisar esses gastos.",
            'category': category['_id'],
            'amount': category['total'],
            'count': category['count']
        }
    
    return None

def check_recurring_transactions(user_id):
    """Verificar lembretes de transações recorrentes"""
    # Implementação simplificada - idealmente seria baseado em transações marcadas como recorrentes
    notifications = []
    
    # Exemplo: lembrar de registrar salário no início do mês
    now = datetime.now()
    if now.day <= 5:  # Primeiros 5 dias do mês
        notifications.append({
            'id': f"recurring_salary_{user_id}_{now.month}",
            'type': 'transaction_reminder',
            'priority': 3,
            'title': 'Lembrete: Registrar Salário',
            'message': 'Não se esqueça de registrar o salário deste mês',
            'created_at': datetime.utcnow().isoformat(),
            'read': False
        })
    
    return notifications

def check_transaction_inactivity(user_id):
    """Verificar inatividade no registro de transações"""
    from app import get_db
    db = get_db()
    
    # Última transação
    last_transaction = db.transactions.find_one(
        {'added_by': ObjectId(user_id)},
        sort=[('date', -1)]
    )
    
    if last_transaction:
        days_since_last = (datetime.now() - last_transaction['date']).days
        
        if days_since_last >= 7:  # 7 dias sem transações
            return {
                'id': f"inactivity_{user_id}",
                'type': 'inactivity_reminder',
                'priority': 3,
                'title': 'Registre suas Transações',
                'message': f'Faz {days_since_last} dias que você não registra uma transação',
                'days_since_last': days_since_last,
                'created_at': datetime.utcnow().isoformat(),
                'read': False
            }
    
    return None