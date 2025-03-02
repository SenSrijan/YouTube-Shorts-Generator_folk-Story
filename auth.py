from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from itsdangerous import URLSafeTimedSerializer
from models import db, User, ApiKey
import uuid
import secrets
import string
from functools import wraps
import re
from email_service import send_reset_password_email

# Initialize Blueprint
auth_bp = Blueprint('auth', __name__)
login_manager = LoginManager()

# Configure for API access
def init_login_manager(app):
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Add unauthorized handler for API requests
    @login_manager.unauthorized_handler
    def unauthorized():
        if request.blueprint == 'api':
            return jsonify({'error': 'Authentication required'}), 401
        return redirect(url_for('auth.login'))


def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key is required'}), 401
            
        key = ApiKey.query.filter_by(api_key=api_key, is_active=True).first()
        if not key:
            return jsonify({'error': 'Invalid API key'}), 401
            
        # Check if user's subscription is active
        user = User.query.get(key.user_id)
        if not user or user.subscription_status != 'active':
            return jsonify({'error': 'Subscription inactive or expired'}), 403
            
        # Check rate limits based on subscription tier
        rate_limits = {
            'free': 10,
            'basic': 100,
            'premium': 1000
        }
        
        if key.daily_requests >= rate_limits.get(user.subscription_tier, 0):
            return jsonify({'error': 'Daily API rate limit exceeded'}), 429
            
        # Increment usage counter
        key.increment_usage()
        db.session.commit()
        
        # Set current user for the request
        kwargs['user'] = user
        return f(*args, **kwargs)
    return decorated_function


def subscription_required(min_tier='basic'):
    """
    Decorator to restrict access based on subscription tier
    min_tier can be 'free', 'basic', or 'premium'
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            tier_levels = {
                'free': 0,
                'basic': 1,
                'premium': 2
            }
            
            user_tier_level = tier_levels.get(current_user.subscription_tier, -1)
            required_tier_level = tier_levels.get(min_tier, 1)
            
            if user_tier_level < required_tier_level:
                flash(f'This feature requires a {min_tier} subscription or higher.', 'warning')
                return redirect(url_for('dashboard.index'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Authentication routes
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Basic validation
        if not (email and username and password):
            flash('All fields are required', 'error')
            return render_template('auth/register.html')
            
        if len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
            return render_template('auth/register.html')
            
        if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
            flash('Please enter a valid email address', 'error')
            return render_template('auth/register.html')
            
        # Check if user already exists
        existing_user = User.query.filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if existing_user:
            flash('User with that email or username already exists', 'error')
            return render_template('auth/register.html')
            
        # Create new user
        new_user = User(
            email=email,
            username=username
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            flash('Invalid email or password', 'error')
            return render_template('auth/login.html')
            
        if not user.is_active:
            flash('Your account has been deactivated. Please contact support.', 'error')
            return render_template('auth/login.html')
            
        login_user(user, remember=remember)
        next_page = request.args.get('next', '')
        
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect(url_for('dashboard.index'))
        
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate token
            s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            token = s.dumps(email, salt='password-reset-salt')
            
            # Send password reset email
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            send_reset_password_email(user.email, reset_url)
            
        # Always show the same message to prevent email enumeration
        flash('If your email is registered, you will receive password reset instructions.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password_request.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    try:
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        email = s.loads(token, salt='password-reset-salt', max_age=3600)  # 1 hour expiry
    except:
        flash('The password reset link is invalid or has expired.', 'error')
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/reset_password.html', token=token)
            
        if len(password) < 8:
            flash('Password must be at least 8 characters', 'error')
            return render_template('auth/reset_password.html', token=token)
            
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(password)
            db.session.commit()
            flash('Your password has been reset.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('User not found.', 'error')
            return redirect(url_for('auth.login'))
            
    return render_template('auth/reset_password.html', token=token)


@auth_bp.route('/api-keys', methods=['GET'])
@login_required
def api_keys_list():
    """View all API keys for the current user"""
    api_keys = ApiKey.query.filter_by(user_id=current_user.id).all()
    return render_template('auth/api_keys.html', api_keys=api_keys)


@auth_bp.route('/api-keys/create', methods=['POST'])
@login_required
def create_api_key():
    """Create a new API key"""
    name = request.form.get('name', 'API Key')
    
    # Generate a secure random API key
    alphabet = string.ascii_letters + string.digits
    api_key = ''.join(secrets.choice(alphabet) for _ in range(32))
    
    new_key = ApiKey(
        user_id=current_user.id,
        api_key=api_key,
        name=name
    )
    
    db.session.add(new_key)
    db.session.commit()
    
    flash('API key created successfully.', 'success')
    return redirect(url_for('auth.api_keys_list'))


@auth_bp.route('/api-keys/<int:key_id>/deactivate', methods=['POST'])
@login_required
def deactivate_api_key(key_id):
    """Deactivate an API key"""
    key = ApiKey.query.filter_by(id=key_id, user_id=current_user.id).first()
    
    if not key:
        flash('API key not found.', 'error')
        return redirect(url_for('auth.api_keys_list'))
        
    key.is_active = False
    db.session.commit()
    
    flash('API key deactivated successfully.', 'success')
    return redirect(url_for('auth.api_keys_list'))