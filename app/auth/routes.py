from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from app.models import User
from app import mongo
import re

auth = Blueprint('auth', __name__)

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        
        # Validações
        errors = []
        
        if not name or len(name) < 2:
            errors.append('Nome deve ter pelo menos 2 caracteres')
        
        if not email or not is_valid_email(email):
            errors.append('Email inválido')
        
        if not password or len(password) < 6:
            errors.append('Senha deve ter pelo menos 6 caracteres')
        
        if password != confirm_password:
            errors.append('Senhas não conferem')
        
        # Verificar se email já existe
        if User.find_by_email(email):
            errors.append('Email já cadastrado')
        
        if errors:
            if request.is_json:
                return jsonify({'success': False, 'errors': errors}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html', name=name, email=email)
        
        # Criar usuário
        try:
            user = User(email, name)
            user.set_password(password)
            user_id = user.save()
            
            if request.is_json:
                return jsonify({
                    'success': True, 
                    'message': 'Usuário criado com sucesso!'
                })
            
            flash('Conta criada com sucesso! Faça login.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            error_msg = 'Erro ao criar conta. Tente novamente.'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 500
            flash(error_msg, 'error')
    
    return render_template('auth/register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        remember = data.get('remember', False)
        
        if not email or not password:
            error_msg = 'Email e senha são obrigatórios'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('auth/login.html', email=email)
        
        # Verificar credenciais
        user = User.find_by_email(email)
        
        if user and user.check_password(password):
            # Salvar na sessão
            session['user_id'] = str(user._id)
            session['user_name'] = user.name
            session['user_email'] = user.email
            
            # Gerar token JWT
            token = user.generate_token()
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'token': token,
                    'user': {
                        'id': str(user._id),
                        'name': user.name,
                        'email': user.email
                    }
                })
            
            flash(f'Bem-vindo, {user.name}!', 'success')
            
            # Redirect para próxima página ou dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.overview'))
        
        else:
            error_msg = 'Email ou senha incorretos'
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 401
            flash(error_msg, 'error')
    
    return render_template('auth/login.html')

@auth.route('/logout')
def logout():
    session.clear()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.find_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    
    return render_template('auth/profile.html', user=user)

@auth.route('/api/me')
@jwt_required()
def api_me():
    user_id = get_jwt_identity()
    user = User.find_by_id(user_id)
    
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    
    return jsonify({
        'id': str(user._id),
        'name': user.name,
        'email': user.email,
        'families': [str(fam_id) for fam_id in user.families],
        'default_family': str(user.default_family) if user.default_family else None
    })

# Middleware para verificar login em rotas protegidas
def login_required(f):
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Login necessário'}), 401
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function