from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Subscription related fields
    subscription_tier = db.Column(db.String(20), default='free')  # free, basic, premium
    subscription_status = db.Column(db.String(20), default='active')  # active, canceled, expired
    subscription_expiry = db.Column(db.DateTime, nullable=True)
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    
    # Usage metrics
    monthly_generations = db.Column(db.Integer, default=0)
    total_generations = db.Column(db.Integer, default=0)
    last_generation_date = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    generations = db.relationship('Generation', backref='user', lazy=True)
    api_keys = db.relationship('ApiKey', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def can_generate(self):
        # Check if user has reached their generation limit based on subscription tier
        limits = {
            'free': 3,
            'basic': 30,
            'premium': float('inf')  # Unlimited
        }
        return self.monthly_generations < limits.get(self.subscription_tier, 0)
    
    def increment_generation_count(self):
        self.monthly_generations += 1
        self.total_generations += 1
        self.last_generation_date = datetime.utcnow()
        
    def reset_monthly_generations(self):
        self.monthly_generations = 0
        

class Generation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    generation_id = db.Column(db.String(120), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Content paths
    story_path = db.Column(db.String(255))
    voiceover_path = db.Column(db.String(255))
    voiceover_tts_path = db.Column(db.String(255))
    scenes_path = db.Column(db.String(255))
    
    # Metadata
    is_public = db.Column(db.Boolean, default=False)  # Allow users to publish their generations
    download_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)


class ApiKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Usage tracking
    daily_requests = db.Column(db.Integer, default=0)
    total_requests = db.Column(db.Integer, default=0)
    
    def increment_usage(self):
        self.daily_requests += 1
        self.total_requests += 1
        self.last_used = datetime.utcnow()
        
    def reset_daily_usage(self):
        self.daily_requests = 0


class SubscriptionPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    stripe_price_id = db.Column(db.String(100), unique=True, nullable=False)
    monthly_generations = db.Column(db.Integer, nullable=False)
    price_monthly = db.Column(db.Float, nullable=False)
    features = db.Column(db.Text, nullable=False)  # JSON string of features
    is_active = db.Column(db.Boolean, default=True)


class PaymentHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stripe_payment_id = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # succeeded, failed, pending
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    subscription_plan = db.Column(db.String(50), nullable=False)