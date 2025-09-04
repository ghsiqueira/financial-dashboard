from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from app.auth.routes import login_required
from app.models import User, Transaction
from bson.objectid import ObjectId
from datetime import datetime
import csv
import io

transactions = Blueprint('transactions', __name__)

@transactions.route('/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        try:
            user_id = session['user_id']
            user = User.find_by_id(user_id)
            
            # Determinar conta (individual ou família)
            account_type = data.get('account_type', 'individual')
            if account_type == 'family':
                owner_type = 'family'
                owner_id = data.get('family_id') or user.default_family
                if not owner_id:
                    raise ValueError('Família não selecionada')
            else:
                owner_type = 'individual'
                owner_id = user_id
            
            # Validar dados
            amount = float(data.get('amount', 0))
            if amount <= 0:
                raise ValueError('Valor deve ser maior que zero')
            
            transaction_type = data.get('type')
            if transaction_type not in ['income', 'expense']:
                raise ValueError('Tipo de transação inválido')
            
            category = data.get('category', '').strip()
            description = data.get('description', '').strip()
            
            if not category:
                raise ValueError('Categoria é obrigatória')
            
            # Criar transação
            transaction = Transaction(
                owner_type=owner_type,
                owner_id=owner_id,
                added_by=user_id,
                trans_type=transaction_type,
                amount=amount,
                category=category,
                description=description
            )
            
            # Campos opcionais
            transaction.payment_method = data.get('payment_method')
            transaction.tags = data.get('tags', '').split(',') if data.get('tags') else []
            
            # Data personalizada
            if data.get('date'):
                transaction.date = datetime.strptime(data.get('date'), '%Y-%m-%d')
            
            transaction_id = transaction.save()
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Transação adicionada com sucesso!',
                    'transaction_id': str(transaction_id)
                })
            
            flash('Transação adicionada com sucesso!', 'success')
            return redirect(url_for('dashboard.transactions'))
            
        except ValueError as e:
            error_msg = str(e)
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            flash(error_msg, 'error')
        except Exception as e:
            error_msg = 'Erro ao adicionar transação'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 500
            flash(error_msg, 'error')
    
    # GET request - mostrar formulário
    user = User.find_by_id(session['user_id'])
    categories = get_common_categories()
    
    return render_template('transactions/add.html', user=user, categories=categories)

@transactions.route('/edit/<transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    from app import mongo
    
    try:
        # Buscar transação
        transaction = mongo.db.transactions.find_one({'_id': ObjectId(transaction_id)})
        if not transaction:
            flash('Transação não encontrada', 'error')
            return redirect(url_for('dashboard.transactions'))
        
        # Verificar permissão
        user_id = session['user_id']
        if str(transaction['added_by']) != user_id:
            # Verificar se é admin da família
            if transaction['owner_type'] == 'family':
                if not check_family_permission(user_id, transaction['owner_id'], 'edit_transactions'):
                    flash('Sem permissão para editar esta transação', 'error')
                    return redirect(url_for('dashboard.transactions'))
            else:
                flash('Sem permissão para editar esta transação', 'error')
                return redirect(url_for('dashboard.transactions'))
        
        if request.method == 'POST':
            data = request.get_json() if request.is_json else request.form
            
            # Validar e atualizar dados
            update_data = {}
            
            if 'amount' in data:
                amount = float(data['amount'])
                if amount <= 0:
                    raise ValueError('Valor deve ser maior que zero')
                update_data['amount'] = amount
            
            if 'type' in data:
                if data['type'] not in ['income', 'expense']:
                    raise ValueError('Tipo de transação inválido')
                update_data['type'] = data['type']
            
            if 'category' in data:
                category = data['category'].strip()
                if not category:
                    raise ValueError('Categoria é obrigatória')
                update_data['category'] = category
            
            if 'description' in data:
                update_data['description'] = data['description'].strip()
            
            if 'payment_method' in data:
                update_data['payment_method'] = data['payment_method']
            
            if 'tags' in data:
                update_data['tags'] = data['tags'].split(',') if data['tags'] else []
            
            if 'date' in data and data['date']:
                update_data['date'] = datetime.strptime(data['date'], '%Y-%m-%d')
            
            # Atualizar no banco
            mongo.db.transactions.update_one(
                {'_id': ObjectId(transaction_id)},
                {'$set': update_data}
            )
            
            if request.is_json:
                return jsonify({'success': True, 'message': 'Transação atualizada com sucesso!'})
            
            flash('Transação atualizada com sucesso!', 'success')
            return redirect(url_for('dashboard.transactions'))
        
        # GET request - mostrar formulário de edição
        user = User.find_by_id(session['user_id'])
        categories = get_common_categories()
        
        return render_template('transactions/edit.html', 
                             user=user, 
                             transaction=transaction, 
                             categories=categories)
        
    except ValueError as e:
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 400
        flash(str(e), 'error')
        return redirect(url_for('dashboard.transactions'))
    except Exception as e:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Erro ao atualizar transação'}), 500
        flash('Erro ao atualizar transação', 'error')
        return redirect(url_for('dashboard.transactions'))

@transactions.route('/delete/<transaction_id>', methods=['POST', 'DELETE'])
@login_required
def delete_transaction(transaction_id):
    from app import mongo
    
    try:
        # Buscar transação
        transaction = mongo.db.transactions.find_one({'_id': ObjectId(transaction_id)})
        if not transaction:
            return jsonify({'success': False, 'error': 'Transação não encontrada'}), 404
        
        # Verificar permissão
        user_id = session['user_id']
        if str(transaction['added_by']) != user_id:
            if transaction['owner_type'] == 'family':
                if not check_family_permission(user_id, transaction['owner_id'], 'delete_transactions'):
                    return jsonify({'success': False, 'error': 'Sem permissão'}), 403
            else:
                return jsonify({'success': False, 'error': 'Sem permissão'}), 403
        
        # Deletar
        mongo.db.transactions.delete_one({'_id': ObjectId(transaction_id)})
        
        return jsonify({'success': True, 'message': 'Transação excluída com sucesso!'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Erro ao excluir transação'}), 500

@transactions.route('/import', methods=['GET', 'POST'])
@login_required
def import_transactions():
    if request.method == 'POST':
        try:
            user_id = session['user_id']
            user = User.find_by_id(user_id)
            
            # Verificar se arquivo foi enviado
            if 'file' not in request.files:
                flash('Nenhum arquivo selecionado', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                flash('Nenhum arquivo selecionado', 'error')
                return redirect(request.url)
            
            if not file.filename.lower().endswith('.csv'):
                flash('Apenas arquivos CSV são aceitos', 'error')
                return redirect(request.url)
            
            # Determinar conta
            account_type = request.form.get('account_type', 'individual')
            if account_type == 'family':
                owner_type = 'family'
                owner_id = request.form.get('family_id') or user.default_family
            else:
                owner_type = 'individual'
                owner_id = user_id
            
            # Processar CSV
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)
            
            imported_count = 0
            errors = []
            
            for row_num, row in enumerate(csv_input, start=2):
                try:
                    # Mapear campos do CSV
                    amount = float(row.get('valor', row.get('amount', 0)))
                    if amount <= 0:
                        errors.append(f"Linha {row_num}: Valor inválido")
                        continue
                    
                    transaction_type = row.get('tipo', row.get('type', '')).lower()
                    if transaction_type not in ['receita', 'despesa', 'income', 'expense']:
                        errors.append(f"Linha {row_num}: Tipo inválido (use 'receita' ou 'despesa')")
                        continue
                    
                    # Normalizar tipo
                    if transaction_type in ['receita', 'income']:
                        transaction_type = 'income'
                    else:
                        transaction_type = 'expense'
                    
                    category = row.get('categoria', row.get('category', '')).strip()
                    if not category:
                        category = 'Importado'
                    
                    description = row.get('descricao', row.get('description', '')).strip()
                    
                    # Data
                    date_str = row.get('data', row.get('date', ''))
                    transaction_date = datetime.now()
                    if date_str:
                        try:
                            # Tentar vários formatos de data
                            for date_format in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                                try:
                                    transaction_date = datetime.strptime(date_str, date_format)
                                    break
                                except ValueError:
                                    continue
                        except:
                            pass
                    
                    # Criar transação
                    transaction = Transaction(
                        owner_type=owner_type,
                        owner_id=owner_id,
                        added_by=user_id,
                        trans_type=transaction_type,
                        amount=amount,
                        category=category,
                        description=description
                    )
                    transaction.date = transaction_date
                    transaction.save()
                    
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Linha {row_num}: {str(e)}")
            
            # Resultado da importação
            if imported_count > 0:
                flash(f'{imported_count} transações importadas com sucesso!', 'success')
            
            if errors:
                error_msg = f'{len(errors)} erros encontrados: ' + '; '.join(errors[:5])
                if len(errors) > 5:
                    error_msg += f' (e mais {len(errors) - 5} erros...)'
                flash(error_msg, 'warning')
            
            return redirect(url_for('dashboard.transactions'))
            
        except Exception as e:
            flash(f'Erro ao importar arquivo: {str(e)}', 'error')
    
    # GET request - mostrar formulário
    user = User.find_by_id(session['user_id'])
    return render_template('transactions/import.html', user=user)

@transactions.route('/export')
@login_required
def export_transactions():
    from flask import make_response
    import csv
    import io
    
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        # Parâmetros de filtro
        account_type = request.args.get('account', 'individual')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Determinar conta
        if account_type == 'family' and user.default_family:
            owner_type = 'family'
            owner_id = user.default_family
        else:
            owner_type = 'individual'
            owner_id = user_id
        
        # Buscar transações
        from app import mongo
        query = {
            'owner_id': ObjectId(owner_id),
            'owner_type': owner_type
        }
        
        if date_from and date_to:
            query['date'] = {
                '$gte': datetime.strptime(date_from, '%Y-%m-%d'),
                '$lte': datetime.strptime(date_to, '%Y-%m-%d')
            }
        
        transactions = mongo.db.transactions.find(query).sort('date', -1)
        
        # Criar CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Cabeçalho
        writer.writerow(['Data', 'Tipo', 'Categoria', 'Descrição', 'Valor', 'Método de Pagamento'])
        
        # Dados
        for transaction in transactions:
            writer.writerow([
                transaction['date'].strftime('%d/%m/%Y'),
                'Receita' if transaction['type'] == 'income' else 'Despesa',
                transaction['category'],
                transaction.get('description', ''),
                f"{transaction['amount']:.2f}".replace('.', ','),
                transaction.get('payment_method', '')
            ])
        
        # Criar resposta
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=transacoes_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return response
        
    except Exception as e:
        flash('Erro ao exportar transações', 'error')
        return redirect(url_for('dashboard.transactions'))

# API endpoints
@transactions.route('/api/categories')
@login_required
def api_categories():
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    account_type = request.args.get('account', 'individual')
    if account_type == 'family' and user.default_family:
        owner_type = 'family'
        owner_id = user.default_family
    else:
        owner_type = 'individual'
        owner_id = user_id
    
    categories = get_user_categories(owner_id, owner_type)
    return jsonify(categories)

@transactions.route('/api/recent')
@login_required
def api_recent_transactions():
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    limit = int(request.args.get('limit', 10))
    account_type = request.args.get('account', 'individual')
    
    if account_type == 'family' and user.default_family:
        owner_type = 'family'
        owner_id = user.default_family
    else:
        owner_type = 'individual'
        owner_id = user_id
    
    transactions = Transaction.get_user_transactions(user_id, owner_type, owner_id, limit)
    
    # Converter ObjectId para string
    for transaction in transactions:
        transaction['_id'] = str(transaction['_id'])
        transaction['owner_id'] = str(transaction['owner_id'])
        transaction['added_by'] = str(transaction['added_by'])
        transaction['date'] = transaction['date'].isoformat()
    
    return jsonify(transactions)

# Funções auxiliares
def get_common_categories():
    """Retorna categorias comuns para facilitar seleção"""
    return [
        'Alimentação', 'Transporte', 'Moradia', 'Saúde', 'Educação',
        'Lazer', 'Vestuário', 'Beleza', 'Tecnologia', 'Viagem',
        'Investimentos', 'Presente', 'Pet', 'Doação', 'Outros'
    ]

def get_user_categories(owner_id, owner_type):
    """Busca categorias já utilizadas pelo usuário"""
    from app import mongo
    
    pipeline = [
        {'$match': {'owner_id': ObjectId(owner_id), 'owner_type': owner_type}},
        {'$group': {'_id': '$category'}},
        {'$sort': {'_id': 1}}
    ]
    
    result = mongo.db.transactions.aggregate(pipeline)
    categories = [item['_id'] for item in result if item['_id']]
    
    # Adicionar categorias comuns que ainda não foram usadas
    common = get_common_categories()
    for cat in common:
        if cat not in categories:
            categories.append(cat)
    
    return sorted(categories)

def check_family_permission(user_id, family_id, permission):
    """Verifica se usuário tem permissão específica na família"""
    from app import mongo
    
    family = mongo.db.families.find_one({'_id': ObjectId(family_id)})
    if not family:
        return False
    
    for member in family.get('members', []):
        if str(member['user_id']) == user_id:
            return permission in member.get('permissions', [])
    
    return False