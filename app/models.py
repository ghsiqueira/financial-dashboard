from datetime import datetime, timedelta
from bson.objectid import ObjectId
from flask import current_app
from app import bcrypt
from flask_jwt_extended import create_access_token

def get_db():
    """Helper para obter a instância do mongo dentro do contexto da app"""
    from app import get_db
    return get_db()

class User:
    def __init__(self, email, name, password_hash=None):
        self.email = email
        self.name = name
        self.password_hash = password_hash
        self.families = []
        self.default_family = None
        self.individual_account = True
        self.created_at = datetime.utcnow()
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def save(self):
        db = get_db()
        user_data = {
            'email': self.email,
            'name': self.name,
            'password_hash': self.password_hash,
            'families': self.families,
            'default_family': self.default_family,
            'individual_account': self.individual_account,
            'created_at': self.created_at
        }
        result = db.users.insert_one(user_data)
        self._id = result.inserted_id
        return result.inserted_id
    
    @staticmethod
    def find_by_email(email):
        db = get_db()
        user_data = db.users.find_one({'email': email})
        if user_data:
            user = User(user_data['email'], user_data['name'])
            user.password_hash = user_data['password_hash']
            user.families = user_data.get('families', [])
            user.default_family = user_data.get('default_family')
            user.individual_account = user_data.get('individual_account', True)
            user._id = user_data['_id']
            user.created_at = user_data.get('created_at', datetime.utcnow())
            return user
        return None
    
    @staticmethod
    def find_by_id(user_id):
        db = get_db()
        user_data = db.users.find_one({'_id': ObjectId(user_id)})
        if user_data:
            user = User(user_data['email'], user_data['name'])
            user.password_hash = user_data['password_hash']
            user.families = user_data.get('families', [])
            user.default_family = user_data.get('default_family')
            user.individual_account = user_data.get('individual_account', True)
            user._id = user_data['_id']
            user.created_at = user_data.get('created_at', datetime.utcnow())
            return user
        return None
    
    def generate_token(self):
        return create_access_token(identity=str(self._id), expires_delta=timedelta(days=1))

class Family:
    def __init__(self, name, description, created_by):
        self.name = name
        self.description = description
        self.created_by = ObjectId(created_by)
        self.members = []
        self.settings = {
            'currency': 'BRL',
            'budget_alerts': True,
            'shared_categories': True
        }
        self.created_at = datetime.utcnow()
    
    def add_member(self, user_id, role='member'):
        member = {
            'user_id': ObjectId(user_id),
            'role': role,
            'joined_at': datetime.utcnow(),
            'permissions': self.get_default_permissions(role)
        }
        self.members.append(member)
    
    def get_default_permissions(self, role):
        permissions_map = {
            'admin': ['add_transactions', 'edit_transactions', 'delete_transactions', 
                     'edit_budgets', 'view_investments', 'manage_members'],
            'member': ['add_transactions', 'edit_own_transactions', 'view_all'],
            'viewer': ['view_dashboard', 'view_reports']
        }
        return permissions_map.get(role, [])
    
    def save(self):
        db = get_db()
        family_data = {
            'name': self.name,
            'description': self.description,
            'created_by': self.created_by,
            'members': self.members,
            'settings': self.settings,
            'created_at': self.created_at
        }
        result = db.families.insert_one(family_data)
        self._id = result.inserted_id
        return result.inserted_id
    
    @staticmethod
    def find_by_id(family_id):
        db = get_db()
        family_data = db.families.find_one({'_id': ObjectId(family_id)})
        if family_data:
            family = Family(
                family_data['name'],
                family_data['description'],
                family_data['created_by']
            )
            family.members = family_data.get('members', [])
            family.settings = family_data.get('settings', {})
            family._id = family_data['_id']
            family.created_at = family_data.get('created_at', datetime.utcnow())
            return family
        return None

class Transaction:
    def __init__(self, owner_type, owner_id, added_by, trans_type, amount, category, description):
        self.owner_type = owner_type  # 'family' ou 'individual'
        self.owner_id = ObjectId(owner_id)
        self.added_by = ObjectId(added_by)
        self.type = trans_type  # 'income' ou 'expense'
        self.amount = float(amount)
        self.category = category
        self.description = description
        self.date = datetime.utcnow()
        self.tags = []
        self.payment_method = None
        self.recurring = False
        self.attachments = []
    
    def save(self):
        db = get_db()
        transaction_data = {
            'owner_type': self.owner_type,
            'owner_id': self.owner_id,
            'added_by': self.added_by,
            'type': self.type,
            'amount': self.amount,
            'category': self.category,
            'description': self.description,
            'date': self.date,
            'tags': self.tags,
            'payment_method': self.payment_method,
            'recurring': self.recurring,
            'attachments': self.attachments
        }
        result = db.transactions.insert_one(transaction_data)
        self._id = result.inserted_id
        return result.inserted_id
    
    @staticmethod
    def get_user_transactions(user_id, owner_type='individual', owner_id=None, limit=50):
        db = get_db()
        query = {'added_by': ObjectId(user_id)}
        
        if owner_type == 'family' and owner_id:
            query = {'owner_id': ObjectId(owner_id), 'owner_type': 'family'}
        elif owner_type == 'individual':
            query['owner_type'] = 'individual'
        
        transactions = db.transactions.find(query).sort('date', -1).limit(limit)
        return list(transactions)
    
    @staticmethod
    def get_monthly_summary(owner_id, owner_type='individual', year=None, month=None):
        db = get_db()
        
        if not year:
            year = datetime.now().year
        if not month:
            month = datetime.now().month
        
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        pipeline = [
            {
                '$match': {
                    'owner_id': ObjectId(owner_id),
                    'owner_type': owner_type,
                    'date': {'$gte': start_date, '$lt': end_date}
                }
            },
            {
                '$group': {
                    '_id': '$type',
                    'total': {'$sum': '$amount'},
                    'count': {'$sum': 1}
                }
            }
        ]
        
        result = list(db.transactions.aggregate(pipeline))
        summary = {'income': 0, 'expense': 0, 'balance': 0}
        
        for item in result:
            summary[item['_id']] = item['total']
        
        summary['balance'] = summary['income'] - summary['expense']
        return summary

class Budget:
    def __init__(self, owner_id, owner_type, category, limit_amount, period='monthly'):
        self.owner_id = ObjectId(owner_id)
        self.owner_type = owner_type
        self.category = category
        self.limit = float(limit_amount)
        self.period = period  # 'monthly', 'weekly', 'yearly'
        self.current_spent = 0.0
        self.alerts_enabled = True
        self.created_at = datetime.utcnow()
    
    def save(self):
        db = get_db()
        budget_data = {
            'owner_id': self.owner_id,
            'owner_type': self.owner_type,
            'category': self.category,
            'limit': self.limit,
            'period': self.period,
            'current_spent': self.current_spent,
            'alerts_enabled': self.alerts_enabled,
            'created_at': self.created_at
        }
        result = db.budgets.insert_one(budget_data)
        self._id = result.inserted_id
        return result.inserted_id
    
    def update_spent_amount(self):
        db = get_db()
        
        # Calcula gastos do período atual
        now = datetime.utcnow()
        if self.period == 'monthly':
            start_date = datetime(now.year, now.month, 1)
        elif self.period == 'weekly':
            start_date = now - timedelta(days=now.weekday())
        else:  # yearly
            start_date = datetime(now.year, 1, 1)
        
        pipeline = [
            {
                '$match': {
                    'owner_id': self.owner_id,
                    'owner_type': self.owner_type,
                    'category': self.category,
                    'type': 'expense',
                    'date': {'$gte': start_date}
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
        self.current_spent = result[0]['total'] if result else 0.0
        
        # Atualizar no banco
        if hasattr(self, '_id'):
            db.budgets.update_one(
                {'_id': self._id},
                {'$set': {'current_spent': self.current_spent}}
            )