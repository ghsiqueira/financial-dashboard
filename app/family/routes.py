from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.auth.routes import login_required
from app.models import User, Family
from bson.objectid import ObjectId
from datetime import datetime
import secrets
import string

family = Blueprint('family', __name__)

@family.route('/create', methods=['GET', 'POST'])
@login_required
def create_family():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        try:
            user_id = session['user_id']
            
            name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            
            if not name:
                raise ValueError('Nome da família é obrigatório')
            
            if len(name) < 3:
                raise ValueError('Nome deve ter pelo menos 3 caracteres')
            
            # Criar família
            new_family = Family(name, description, user_id)
            new_family.add_member(user_id, 'admin')  # Criador é admin
            
            family_id = new_family.save()
            
            # Adicionar família ao usuário
            from app import mongo
            mongo.db.users.update_one(
                {'_id': ObjectId(user_id)},
                {
                    '$push': {'families': family_id},
                    '$set': {'default_family': family_id}
                }
            )
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Família criada com sucesso!',
                    'family_id': str(family_id)
                })
            
            flash('Família criada com sucesso!', 'success')
            return redirect(url_for('family.manage', family_id=family_id))
            
        except ValueError as e:
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)}), 400
            flash(str(e), 'error')
        except Exception as e:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Erro ao criar família'}), 500
            flash('Erro ao criar família', 'error')
    
    user = User.find_by_id(session['user_id'])
    return render_template('family/create.html', user=user)

@family.route('/manage/<family_id>')
@login_required
def manage(family_id):
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        # Verificar se usuário pertence à família
        if ObjectId(family_id) not in user.families:
            flash('Você não tem acesso a esta família', 'error')
            return redirect(url_for('dashboard.overview'))
        
        # Buscar dados da família
        family_obj = Family.find_by_id(family_id)
        if not family_obj:
            flash('Família não encontrada', 'error')
            return redirect(url_for('dashboard.overview'))
        
        # Buscar dados dos membros
        members_data = []
        for member in family_obj.members:
            member_user = User.find_by_id(member['user_id'])
            if member_user:
                members_data.append({
                    'user': member_user,
                    'role': member['role'],
                    'joined_at': member['joined_at'],
                    'permissions': member['permissions']
                })
        
        # Verificar se é admin
        user_role = get_user_role_in_family(user_id, family_obj)
        
        context = {
            'user': user,
            'family': family_obj,
            'members': members_data,
            'user_role': user_role,
            'is_admin': user_role == 'admin'
        }
        
        return render_template('family/manage.html', **context)
        
    except Exception as e:
        flash('Erro ao carregar família', 'error')
        return redirect(url_for('dashboard.overview'))

@family.route('/invite', methods=['GET', 'POST'])
@login_required
def invite():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        try:
            user_id = session['user_id']
            family_id = data.get('family_id')
            email = data.get('email', '').strip().lower()
            role = data.get('role', 'member')
            
            if not family_id or not email:
                raise ValueError('Família e email são obrigatórios')
            
            if role not in ['admin', 'member', 'viewer']:
                raise ValueError('Papel inválido')
            
            # Verificar se usuário é admin da família
            family_obj = Family.find_by_id(family_id)
            if not family_obj:
                raise ValueError('Família não encontrada')
            
            user_role = get_user_role_in_family(user_id, family_obj)
            if user_role != 'admin':
                raise ValueError('Apenas administradores podem convidar membros')
            
            # Verificar se usuário convidado existe
            invited_user = User.find_by_email(email)
            if not invited_user:
                raise ValueError('Usuário não encontrado com este email')
            
            # Verificar se já é membro
            for member in family_obj.members:
                if member['user_id'] == invited_user._id:
                    raise ValueError('Usuário já é membro desta família')
            
            # Gerar convite
            invite_code = generate_invite_code()
            
            # Salvar convite no banco
            from app import mongo
            invite_data = {
                'family_id': ObjectId(family_id),
                'invited_by': ObjectId(user_id),
                'invited_user_id': invited_user._id,
                'email': email,
                'role': role,
                'code': invite_code,
                'status': 'pending',
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow().replace(hour=23, minute=59, second=59)  # Expira no final do dia
            }
            
            mongo.db.invites.insert_one(invite_data)
            
            # TODO: Enviar email com convite
            # send_invite_email(invited_user.email, family_obj.name, invite_code)
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': f'Convite enviado para {email}',
                    'invite_code': invite_code
                })
            
            flash(f'Convite enviado para {email}! Código: {invite_code}', 'success')
            return redirect(url_for('family.manage', family_id=family_id))
            
        except ValueError as e:
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)}), 400
            flash(str(e), 'error')
        except Exception as e:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Erro ao enviar convite'}), 500
            flash('Erro ao enviar convite', 'error')
    
    # GET - mostrar formulário
    family_id = request.args.get('family_id')
    user = User.find_by_id(session['user_id'])
    
    if family_id:
        family_obj = Family.find_by_id(family_id)
        if family_obj and get_user_role_in_family(session['user_id'], family_obj) == 'admin':
            return render_template('family/invite.html', user=user, family=family_obj)
    
    flash('Família não encontrada ou sem permissão', 'error')
    return redirect(url_for('dashboard.overview'))

@family.route('/join', methods=['GET', 'POST'])
@login_required
def join():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        try:
            user_id = session['user_id']
            invite_code = data.get('invite_code', '').strip()
            
            if not invite_code:
                raise ValueError('Código de convite é obrigatório')
            
            # Buscar convite
            from app import mongo
            invite = mongo.db.invites.find_one({
                'code': invite_code,
                'status': 'pending',
                'expires_at': {'$gte': datetime.utcnow()}
            })
            
            if not invite:
                raise ValueError('Código de convite inválido ou expirado')
            
            # Verificar se o convite é para este usuário
            if invite['invited_user_id'] != ObjectId(user_id):
                raise ValueError('Este convite não é para você')
            
            # Adicionar usuário à família
            family_obj = Family.find_by_id(invite['family_id'])
            if not family_obj:
                raise ValueError('Família não encontrada')
            
            # Verificar se já é membro
            for member in family_obj.members:
                if member['user_id'] == ObjectId(user_id):
                    raise ValueError('Você já é membro desta família')
            
            # Adicionar membro
            family_obj.add_member(user_id, invite['role'])
            
            # Atualizar família no banco
            mongo.db.families.update_one(
                {'_id': family_obj._id},
                {'$set': {'members': family_obj.members}}
            )
            
            # Adicionar família ao usuário
            user_update = {'$push': {'families': family_obj._id}}
            
            # Se é a primeira família, definir como padrão
            user = User.find_by_id(user_id)
            if not user.families:
                user_update['$set'] = {'default_family': family_obj._id}
            
            mongo.db.users.update_one(
                {'_id': ObjectId(user_id)},
                user_update
            )
            
            # Marcar convite como aceito
            mongo.db.invites.update_one(
                {'_id': invite['_id']},
                {'$set': {'status': 'accepted', 'accepted_at': datetime.utcnow()}}
            )
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': f'Você entrou na família {family_obj.name}!',
                    'family_id': str(family_obj._id)
                })
            
            flash(f'Você entrou na família {family_obj.name}!', 'success')
            return redirect(url_for('family.manage', family_id=family_obj._id))
            
        except ValueError as e:
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)}), 400
            flash(str(e), 'error')
        except Exception as e:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Erro ao entrar na família'}), 500
            flash('Erro ao entrar na família', 'error')
    
    user = User.find_by_id(session['user_id'])
    return render_template('family/join.html', user=user)

@family.route('/leave/<family_id>', methods=['POST'])
@login_required
def leave_family(family_id):
    try:
        user_id = session['user_id']
        from app import mongo
        
        # Buscar família
        family_obj = Family.find_by_id(family_id)
        if not family_obj:
            return jsonify({'success': False, 'error': 'Família não encontrada'}), 404
        
        # Verificar se é membro
        user_member = None
        for member in family_obj.members:
            if str(member['user_id']) == user_id:
                user_member = member
                break
        
        if not user_member:
            return jsonify({'success': False, 'error': 'Você não é membro desta família'}), 400
        
        # Verificar se é o último admin
        admin_count = sum(1 for m in family_obj.members if m['role'] == 'admin')
        if user_member['role'] == 'admin' and admin_count == 1:
            return jsonify({
                'success': False, 
                'error': 'Você é o último administrador. Promova outro membro antes de sair.'
            }), 400
        
        # Remover das famílias do usuário
        user_update = {'$pull': {'families': ObjectId(family_id)}}
        
        # Se era a família padrão, limpar
        user = User.find_by_id(user_id)
        if user.default_family == ObjectId(family_id):
            # Definir outra família como padrão ou null
            other_family = None
            for fam_id in user.families:
                if fam_id != ObjectId(family_id):
                    other_family = fam_id
                    break
            
            user_update['$set'] = {'default_family': other_family}
        
        mongo.db.users.update_one({'_id': ObjectId(user_id)}, user_update)
        
        # Remover da lista de membros da família
        mongo.db.families.update_one(
            {'_id': ObjectId(family_id)},
            {'$pull': {'members': {'user_id': ObjectId(user_id)}}}
        )
        
        return jsonify({'success': True, 'message': 'Você saiu da família'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Erro ao sair da família'}), 500

@family.route('/remove_member', methods=['POST'])
@login_required
def remove_member():
    try:
        data = request.get_json()
        user_id = session['user_id']
        family_id = data.get('family_id')
        member_id = data.get('member_id')
        
        if not family_id or not member_id:
            return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
        
        # Verificar se é admin
        family_obj = Family.find_by_id(family_id)
        if not family_obj:
            return jsonify({'success': False, 'error': 'Família não encontrada'}), 404
        
        if get_user_role_in_family(user_id, family_obj) != 'admin':
            return jsonify({'success': False, 'error': 'Apenas administradores podem remover membros'}), 403
        
        # Não pode remover a si mesmo
        if member_id == user_id:
            return jsonify({'success': False, 'error': 'Use a opção "Sair da família" para se remover'}), 400
        
        # Remover membro
        from app import mongo
        
        # Remover da família
        mongo.db.families.update_one(
            {'_id': ObjectId(family_id)},
            {'$pull': {'members': {'user_id': ObjectId(member_id)}}}
        )
        
        # Remover do usuário
        user_update = {'$pull': {'families': ObjectId(family_id)}}
        
        # Se era família padrão, limpar
        member_user = User.find_by_id(member_id)
        if member_user and member_user.default_family == ObjectId(family_id):
            other_family = None
            for fam_id in member_user.families:
                if fam_id != ObjectId(family_id):
                    other_family = fam_id
                    break
            user_update['$set'] = {'default_family': other_family}
        
        mongo.db.users.update_one({'_id': ObjectId(member_id)}, user_update)
        
        return jsonify({'success': True, 'message': 'Membro removido da família'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Erro ao remover membro'}), 500

@family.route('/change_role', methods=['POST'])
@login_required
def change_member_role():
    try:
        data = request.get_json()
        user_id = session['user_id']
        family_id = data.get('family_id')
        member_id = data.get('member_id')
        new_role = data.get('role')
        
        if not all([family_id, member_id, new_role]):
            return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
        
        if new_role not in ['admin', 'member', 'viewer']:
            return jsonify({'success': False, 'error': 'Papel inválido'}), 400
        
        # Verificar se é admin
        family_obj = Family.find_by_id(family_id)
        if not family_obj:
            return jsonify({'success': False, 'error': 'Família não encontrada'}), 404
        
        if get_user_role_in_family(user_id, family_obj) != 'admin':
            return jsonify({'success': False, 'error': 'Apenas administradores podem alterar papéis'}), 403
        
        # Verificar se está tentando rebaixar o último admin
        if new_role != 'admin':
            current_member_role = get_user_role_in_family(member_id, family_obj)
            if current_member_role == 'admin':
                admin_count = sum(1 for m in family_obj.members if m['role'] == 'admin')
                if admin_count == 1:
                    return jsonify({
                        'success': False,
                        'error': 'Não é possível rebaixar o último administrador'
                    }), 400
        
        # Atualizar papel
        from app import mongo
        
        # Obter permissões do novo papel
        permissions = family_obj.get_default_permissions(new_role)
        
        mongo.db.families.update_one(
            {
                '_id': ObjectId(family_id),
                'members.user_id': ObjectId(member_id)
            },
            {
                '$set': {
                    'members.$.role': new_role,
                    'members.$.permissions': permissions
                }
            }
        )
        
        return jsonify({'success': True, 'message': 'Papel alterado com sucesso'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Erro ao alterar papel'}), 500

@family.route('/switch/<family_id>')
@login_required
def switch_family(family_id):
    """Trocar família ativa"""
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        # Verificar se usuário pertence à família
        if ObjectId(family_id) not in user.families:
            flash('Você não tem acesso a esta família', 'error')
            return redirect(url_for('dashboard.overview'))
        
        # Atualizar família padrão
        from app import mongo
        mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'default_family': ObjectId(family_id)}}
        )
        
        family_obj = Family.find_by_id(family_id)
        flash(f'Trocado para família: {family_obj.name}', 'success')
        
        return redirect(url_for('dashboard.overview', account='family'))
        
    except Exception as e:
        flash('Erro ao trocar família', 'error')
        return redirect(url_for('dashboard.overview'))

@family.route('/settings/<family_id>', methods=['GET', 'POST'])
@login_required
def family_settings(family_id):
    try:
        user_id = session['user_id']
        
        # Verificar se é admin
        family_obj = Family.find_by_id(family_id)
        if not family_obj:
            flash('Família não encontrada', 'error')
            return redirect(url_for('dashboard.overview'))
        
        if get_user_role_in_family(user_id, family_obj) != 'admin':
            flash('Apenas administradores podem alterar configurações', 'error')
            return redirect(url_for('family.manage', family_id=family_id))
        
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form
            
            # Atualizar configurações
            settings_update = {}
            
            if 'currency' in data:
                settings_update['settings.currency'] = data['currency']
            
            if 'budget_alerts' in data:
                settings_update['settings.budget_alerts'] = bool(data['budget_alerts'])
            
            if 'shared_categories' in data:
                settings_update['settings.shared_categories'] = bool(data['shared_categories'])
            
            # Atualizar informações básicas
            if 'name' in data and data['name'].strip():
                settings_update['name'] = data['name'].strip()
            
            if 'description' in data:
                settings_update['description'] = data['description'].strip()
            
            if settings_update:
                from app import mongo
                mongo.db.families.update_one(
                    {'_id': ObjectId(family_id)},
                    {'$set': settings_update}
                )
                
                if request.is_json:
                    return jsonify({'success': True, 'message': 'Configurações atualizadas'})
                
                flash('Configurações atualizadas com sucesso!', 'success')
            
            return redirect(url_for('family.family_settings', family_id=family_id))
        
        # GET - mostrar formulário
        user = User.find_by_id(user_id)
        return render_template('family/settings.html', user=user, family=family_obj)
        
    except Exception as e:
        flash('Erro ao carregar configurações', 'error')
        return redirect(url_for('family.manage', family_id=family_id))

@family.route('/api/invites/<family_id>')
@login_required
def api_family_invites(family_id):
    """Listar convites pendentes da família"""
    try:
        user_id = session['user_id']
        
        # Verificar se é admin
        family_obj = Family.find_by_id(family_id)
        if not family_obj or get_user_role_in_family(user_id, family_obj) != 'admin':
            return jsonify({'error': 'Sem permissão'}), 403
        
        # Buscar convites
        from app import mongo
        invites = mongo.db.invites.find({
            'family_id': ObjectId(family_id),
            'status': 'pending'
        }).sort('created_at', -1)
        
        invites_list = []
        for invite in invites:
            invites_list.append({
                'id': str(invite['_id']),
                'email': invite['email'],
                'role': invite['role'],
                'code': invite['code'],
                'created_at': invite['created_at'].isoformat(),
                'expires_at': invite['expires_at'].isoformat()
            })
        
        return jsonify(invites_list)
        
    except Exception as e:
        return jsonify({'error': 'Erro ao buscar convites'}), 500

@family.route('/api/stats/<family_id>')
@login_required
def api_family_stats(family_id):
    """Estatísticas da família"""
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        # Verificar acesso
        if ObjectId(family_id) not in user.families:
            return jsonify({'error': 'Sem acesso'}), 403
        
        from app.models import Transaction
        from app import mongo
        
        # Resumo do mês atual
        summary = Transaction.get_monthly_summary(family_id, 'family')
        
        # Contadores
        family_data = mongo.db.families.find_one(
            {'_id': ObjectId(family_id)},
            {'members': 1}
        )
        member_count = len(family_data['members']) if family_data else 0
        
        transaction_count = mongo.db.transactions.count_documents({
            'owner_id': ObjectId(family_id),
            'owner_type': 'family'
        })
        
        # Membro que mais gastou este mês
        top_spender_pipeline = [
            {
                '$match': {
                    'owner_id': ObjectId(family_id),
                    'owner_type': 'family',
                    'type': 'expense',
                    'date': {
                        '$gte': datetime.now().replace(day=1),
                        '$lt': datetime.now()
                    }
                }
            },
            {
                '$group': {
                    '_id': '$added_by',
                    'total': {'$sum': '$amount'}
                }
            },
            {'$sort': {'total': -1}},
            {'$limit': 1}
        ]
        
        top_spender_result = list(mongo.db.transactions.aggregate(top_spender_pipeline))
        top_spender = None
        
        if top_spender_result:
            top_spender_user = User.find_by_id(top_spender_result[0]['_id'])
            if top_spender_user:
                top_spender = {
                    'name': top_spender_user.name,
                    'amount': top_spender_result[0]['total']
                }
        
        stats = {
            'summary': summary,
            'member_count': member_count,
            'transaction_count': transaction_count,
            'top_spender': top_spender
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': 'Erro ao buscar estatísticas'}), 500

# Funções auxiliares
def get_user_role_in_family(user_id, family_obj):
    """Retorna o papel do usuário na família"""
    for member in family_obj.members:
        if str(member['user_id']) == str(user_id):
            return member['role']
    return None

def generate_invite_code():
    """Gera código de convite único"""
    length = 8
    characters = string.ascii_uppercase + string.digits
    # Evitar caracteres confusos
    characters = characters.replace('0', '').replace('O', '').replace('1', '').replace('I', '')
    
    code = ''.join(secrets.choice(characters) for _ in range(length))
    
    # Verificar se já existe (muito improvável, mas por segurança)
    from app import mongo
    while mongo.db.invites.find_one({'code': code}):
        code = ''.join(secrets.choice(characters) for _ in range(length))
    
    return code

def send_invite_email(email, family_name, invite_code):
    """Envia email de convite (implementar com Flask-Mail)"""
    # TODO: Implementar envio de email
    pass