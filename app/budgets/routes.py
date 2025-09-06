from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from app.auth.routes import login_required
from app.models import User, Budget
from bson.objectid import ObjectId
from datetime import datetime

budgets = Blueprint('budgets', __name__)

@budgets.route('/create', methods=['POST'])
@login_required
def create_budget():
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        data = request.get_json() if request.is_json else request.form
        
        category = data.get('category', '').strip()
        limit_amount = float(data.get('limit', 0))
        period = data.get('period', 'monthly')
        alerts_enabled = bool(data.get('alerts_enabled', True))
        
        if not category:
            raise ValueError('Categoria é obrigatória')
        
        if limit_amount <= 0:
            raise ValueError('Valor limite deve ser maior que zero')
        
        if period not in ['monthly', 'weekly', 'yearly']:
            raise ValueError('Período inválido')
        
        # Determinar conta (individual ou família)
        account_type = data.get('account_type', 'individual')
        if account_type == 'family' and user.default_family:
            owner_type = 'family'
            owner_id = user.default_family
        else:
            owner_type = 'individual'
            owner_id = user_id
        
        # Verificar se já existe orçamento para esta categoria
        from app import get_db
        db = get_db()
        existing = db.budgets.find_one({
            'owner_id': ObjectId(owner_id),
            'owner_type': owner_type,
            'category': category,
            'period': period
        })
        
        if existing:
            raise ValueError(f'Já existe um orçamento {period} para a categoria {category}')
        
        # Criar orçamento
        budget = Budget(owner_id, owner_type, category, limit_amount, period)
        budget.alerts_enabled = alerts_enabled
        budget_id = budget.save()
        
        # Calcular valor gasto atual
        budget._id = budget_id
        budget.update_spent_amount()
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Orçamento criado com sucesso!',
                'budget_id': str(budget_id)
            })
        
        flash('Orçamento criado com sucesso!', 'success')
        return redirect(url_for('dashboard.budgets'))
        
    except ValueError as e:
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 400
        flash(str(e), 'error')
        return redirect(url_for('dashboard.budgets'))
    except Exception as e:
        error_msg = 'Erro ao criar orçamento'
        if request.is_json:
            return jsonify({'success': False, 'error': error_msg}), 500
        flash(error_msg, 'error')
        return redirect(url_for('dashboard.budgets'))

@budgets.route('/edit/<budget_id>', methods=['GET', 'POST'])
@login_required
def edit_budget(budget_id):
    try:
        user_id = session['user_id']
        
        # Buscar orçamento
        from app import get_db
        db = get_db()
        budget_data = db.budgets.find_one({'_id': ObjectId(budget_id)})
        
        if not budget_data:
            flash('Orçamento não encontrado', 'error')
            return redirect(url_for('dashboard.budgets'))
        
        # Verificar permissão
        if str(budget_data['owner_id']) != user_id:
            # Se for família, verificar se tem permissão
            if budget_data['owner_type'] == 'family':
                if not check_family_permission(user_id, budget_data['owner_id'], 'edit_budgets'):
                    flash('Sem permissão para editar este orçamento', 'error')
                    return redirect(url_for('dashboard.budgets'))
            else:
                flash('Sem permissão para editar este orçamento', 'error')
                return redirect(url_for('dashboard.budgets'))
        
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form
            
            update_data = {}
            
            if 'category' in data and data['category'].strip():
                update_data['category'] = data['category'].strip()
            
            if 'limit' in data:
                limit_amount = float(data['limit'])
                if limit_amount <= 0:
                    raise ValueError('Valor limite deve ser maior que zero')
                update_data['limit'] = limit_amount
            
            if 'period' in data:
                period = data['period']
                if period not in ['monthly', 'weekly', 'yearly']:
                    raise ValueError('Período inválido')
                update_data['period'] = period
            
            if 'alerts_enabled' in data:
                update_data['alerts_enabled'] = bool(data['alerts_enabled'])
            
            # Atualizar no banco
            db.budgets.update_one(
                {'_id': ObjectId(budget_id)},
                {'$set': update_data}
            )
            
            # Recalcular valor gasto
            budget = Budget(
                budget_data['owner_id'],
                budget_data['owner_type'],
                update_data.get('category', budget_data['category']),
                update_data.get('limit', budget_data['limit']),
                update_data.get('period', budget_data['period'])
            )
            budget._id = ObjectId(budget_id)
            budget.update_spent_amount()
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Orçamento atualizado com sucesso!'})
            
            flash('Orçamento atualizado com sucesso!', 'success')
            return redirect(url_for('dashboard.budgets'))
        
        # GET - mostrar formulário de edição
        user = User.find_by_id(user_id)
        return render_template('budgets/edit.html', user=user, budget=budget_data)
        
    except ValueError as e:
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 400
        flash(str(e), 'error')
        return redirect(url_for('dashboard.budgets'))
    except Exception as e:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Erro ao atualizar orçamento'}), 500
        flash('Erro ao atualizar orçamento', 'error')
        return redirect(url_for('dashboard.budgets'))

@budgets.route('/delete/<budget_id>', methods=['POST', 'DELETE'])
@login_required
def delete_budget(budget_id):
    try:
        user_id = session['user_id']
        
        # Buscar orçamento
        from app import get_db
        db = get_db()
        budget = db.budgets.find_one({'_id': ObjectId(budget_id)})
        
        if not budget:
            return jsonify({'success': False, 'error': 'Orçamento não encontrado'}), 404
        
        # Verificar permissão
        if str(budget['owner_id']) != user_id:
            if budget['owner_type'] == 'family':
                if not check_family_permission(user_id, budget['owner_id'], 'edit_budgets'):
                    return jsonify({'success': False, 'error': 'Sem permissão'}), 403
            else:
                return jsonify({'success': False, 'error': 'Sem permissão'}), 403
        
        # Deletar
        db.budgets.delete_one({'_id': ObjectId(budget_id)})
        
        return jsonify({'success': True, 'message': 'Orçamento excluído com sucesso!'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Erro ao excluir orçamento'}), 500

@budgets.route('/api/alerts/<owner_id>')
@login_required
def api_budget_alerts(owner_id):
    """Verificar alertas de orçamento"""
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        # Determinar tipo de conta
        if owner_id == user_id:
            owner_type = 'individual'
        elif user.default_family and str(user.default_family) == owner_id:
            owner_type = 'family'
        else:
            return jsonify({'error': 'Sem acesso'}), 403
        
        from app import get_db
        db = get_db()
        
        # Buscar orçamentos com alertas habilitados
        budgets_cursor = db.budgets.find({
            'owner_id': ObjectId(owner_id),
            'owner_type': owner_type,
            'alerts_enabled': True
        })
        
        alerts = []
        
        for budget_data in budgets_cursor:
            # Criar objeto Budget para calcular gasto atual
            budget = Budget(
                budget_data['owner_id'],
                budget_data['owner_type'],
                budget_data['category'],
                budget_data['limit'],
                budget_data['period']
            )
            budget._id = budget_data['_id']
            budget.update_spent_amount()
            
            # Verificar se atingiu 80% ou 100%
            percentage = (budget.current_spent / budget.limit * 100) if budget.limit > 0 else 0
            
            if percentage >= 100:
                alerts.append({
                    'type': 'danger',
                    'category': budget.category,
                    'message': f'Orçamento de {budget.category} excedido!',
                    'percentage': percentage,
                    'spent': budget.current_spent,
                    'limit': budget.limit
                })
            elif percentage >= 80:
                alerts.append({
                    'type': 'warning',
                    'category': budget.category,
                    'message': f'Orçamento de {budget.category} quase esgotado ({percentage:.1f}%)',
                    'percentage': percentage,
                    'spent': budget.current_spent,
                    'limit': budget.limit
                })
        
        return jsonify(alerts)
        
    except Exception as e:
        return jsonify({'error': 'Erro ao buscar alertas'}), 500

@budgets.route('/api/performance/<owner_id>')
@login_required
def api_budget_performance(owner_id):
    """Análise de performance dos orçamentos"""
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        # Verificar acesso
        if owner_id != user_id and (not user.default_family or str(user.default_family) != owner_id):
            return jsonify({'error': 'Sem acesso'}), 403
        
        owner_type = 'individual' if owner_id == user_id else 'family'
        
        from app import get_db
        db = get_db()
        
        # Buscar todos os orçamentos
        budgets_cursor = db.budgets.find({
            'owner_id': ObjectId(owner_id),
            'owner_type': owner_type
        })
        
        performance = {
            'total_budgets': 0,
            'total_limit': 0,
            'total_spent': 0,
            'on_track': 0,
            'near_limit': 0,
            'over_budget': 0,
            'categories': []
        }
        
        for budget_data in budgets_cursor:
            budget = Budget(
                budget_data['owner_id'],
                budget_data['owner_type'],
                budget_data['category'],
                budget_data['limit'],
                budget_data['period']
            )
            budget._id = budget_data['_id']
            budget.update_spent_amount()
            
            percentage = (budget.current_spent / budget.limit * 100) if budget.limit > 0 else 0
            
            performance['total_budgets'] += 1
            performance['total_limit'] += budget.limit
            performance['total_spent'] += budget.current_spent
            
            if percentage >= 100:
                performance['over_budget'] += 1
                status = 'over'
            elif percentage >= 80:
                performance['near_limit'] += 1
                status = 'warning'
            else:
                performance['on_track'] += 1
                status = 'good'
            
            performance['categories'].append({
                'category': budget.category,
                'limit': budget.limit,
                'spent': budget.current_spent,
                'percentage': percentage,
                'status': status,
                'remaining': budget.limit - budget.current_spent
            })
        
        # Calcular médias
        if performance['total_budgets'] > 0:
            performance['average_usage'] = (performance['total_spent'] / performance['total_limit'] * 100) if performance['total_limit'] > 0 else 0
        else:
            performance['average_usage'] = 0
        
        return jsonify(performance)
        
    except Exception as e:
        return jsonify({'error': 'Erro ao analisar performance'}), 500

# Funções auxiliares
def check_family_permission(user_id, family_id, permission):
    """Verifica se usuário tem permissão específica na família"""
    from app import get_db
    
    db = get_db()
    family = db.families.find_one({'_id': ObjectId(family_id)})
    if not family:
        return False
    
    for member in family.get('members', []):
        if str(member['user_id']) == user_id:
            return permission in member.get('permissions', [])
    
    return False