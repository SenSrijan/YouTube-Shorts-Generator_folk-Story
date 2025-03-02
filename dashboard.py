from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from models import db, User, Generation, PaymentHistory, SubscriptionPlan
from datetime import datetime, timedelta
import json
import os

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    """Main dashboard page showing user stats and recent generations"""
    # Get recent generations
    recent_generations = Generation.query.filter_by(user_id=current_user.id)\
        .order_by(Generation.timestamp.desc())\
        .limit(5)\
        .all()
    
    # Calculate usage statistics
    usage_percent = 0
    if current_user.subscription_tier != 'premium':  # Premium has unlimited generations
        plan = SubscriptionPlan.query.filter_by(name=current_user.subscription_tier).first()
        if plan:
            limit = plan.monthly_generations
            usage_percent = (current_user.monthly_generations / limit) * 100 if limit > 0 else 0
    
    # Get subscription details
    current_plan = SubscriptionPlan.query.filter_by(name=current_user.subscription_tier).first()
    days_left = 0
    if current_user.subscription_expiry:
        days_left = (current_user.subscription_expiry - datetime.utcnow()).days
    
    # Get total generations this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_generations_count = Generation.query.filter(
        Generation.user_id == current_user.id,
        Generation.timestamp >= month_start
    ).count()
    
    return render_template('dashboard/index.html',
                          recent_generations=recent_generations,
                          usage_percent=usage_percent,
                          current_plan=current_plan,
                          days_left=days_left,
                          month_generations=month_generations_count,
                          total_generations=current_user.total_generations)


@dashboard_bp.route('/generations')
@login_required
def generations():
    """View all user generations with filtering options"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Filter parameters
    country = request.args.get('country', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Build query
    query = Generation.query.filter_by(user_id=current_user.id)
    
    if country:
        query = query.filter(Generation.country.ilike(f'%{country}%'))
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Generation.timestamp >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
            query = query.filter(Generation.timestamp <= date_to_obj)
        except ValueError:
            pass
    
    # Paginate results
    generations = query.order_by(Generation.timestamp.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('dashboard/generations.html',
                          generations=generations,
                          country=country,
                          date_from=date_from,
                          date_to=date_to)


@dashboard_bp.route('/generation/<generation_id>')
@login_required
def view_generation(generation_id):
    """View details of a specific generation"""
    generation = Generation.query.filter_by(
        generation_id=generation_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Increment view count
    generation.view_count += 1
    db.session.commit()
    
    # Load content files
    content = {}
    base_dir = os.path.join('static', 'outputs', generation.generation_id)
    
    try:
        with open(os.path.join(base_dir, 'story.txt'), 'r', encoding='utf-8') as f:
            content['story'] = f.read()
        
        with open(os.path.join(base_dir, 'voiceover.txt'), 'r', encoding='utf-8') as f:
            content['voiceover'] = f.read()
        
        with open(os.path.join(base_dir, 'scenes.txt'), 'r', encoding='utf-8') as f:
            content['scenes'] = f.read()
        
        with open(os.path.join(base_dir, 'metadata.json'), 'r', encoding='utf-8') as f:
            content['metadata'] = json.load(f)
    except Exception as e:
        flash(f'Error loading content: {str(e)}', 'error')
        content = {
            'story': 'Content not available',
            'voiceover': 'Content not available',
            'scenes': 'Content not available',
            'metadata': {}
        }
    
    return render_template('dashboard/view_generation.html',
                          generation=generation,
                          content=content)


@dashboard_bp.route('/download/<generation_id>/<file_type>')
@login_required
def download_file(generation_id, file_type):
    """Download files associated with a generation"""
    generation = Generation.query.filter_by(
        generation_id=generation_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Map file types to file paths
    file_paths = {
        'story': os.path.join('static', 'outputs', generation_id, 'story.txt'),
        'voiceover': os.path.join('static', 'outputs', generation_id, 'voiceover.txt'),
        'audio': os.path.join('static', 'outputs', generation_id, 'voiceover_tts.mp3'),
        'scenes': os.path.join('static', 'outputs', generation_id, 'scenes.txt'),
        'all': None  # Handled separately for zip downloads
    }
    
    if file_type not in file_paths:
        flash('Invalid file type requested.', 'error')
        return redirect(url_for('dashboard.view_generation', generation_id=generation_id))
    
    # Increment download count
    generation.download_count += 1
    db.session.commit()
    
    if file_type == 'all':
        # Create zip file with all content
        import zipfile
        from io import BytesIO
        
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for name, path in file_paths.items():
                if name != 'all' and os.path.exists(path):
                    zf.write(path, os.path.basename(path))
        
        memory_file.seek(0)
        return send_file(memory_file,
                        download_name=f"{generation_id}_complete.zip",
                        as_attachment=True)
    else:
        return send_file(file_paths[file_type],
                        download_name=os.path.basename(file_paths[file_type]),
                        as_attachment=True)


@dashboard_bp.route('/subscription')
@login_required
def subscription():
    """View and manage subscription details"""
    # Get current plan details
    current_plan = SubscriptionPlan.query.filter_by(name=current_user.subscription_tier).first()
    
    # Get payment history
    payments = PaymentHistory.query.filter_by(user_id=current_user.id)\
        .order_by(PaymentHistory.payment_date.desc())\
        .limit(10)\
        .all()
    
    # Calculate subscription status and next payment date
    status = current_user.subscription_status
    next_payment = current_user.subscription_expiry
    
    return render_template('dashboard/subscription.html',
                          current_plan=current_plan,
                          payments=payments,
                          status=status,
                          next_payment=next_payment)


@dashboard_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """User profile and account settings"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_profile':
            # Update user profile
            username = request.form.get('username')
            
            # Check if username is taken
            if username != current_user.username:
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    flash('Username is already taken.', 'error')
                    return redirect(url_for('dashboard.settings'))
            
            current_user.username = username
            db.session.commit()
            flash('Profile updated successfully.', 'success')
            
        elif action == 'change_password':
            # Change password
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'error')
                return redirect(url_for('dashboard.settings'))
            
            if new_password != confirm_password:
                flash('New passwords do not match.', 'error')
                return redirect(url_for('dashboard.settings'))
            
            if len(new_password) < 8:
                flash('Password must be at least 8 characters.', 'error')
                return redirect(url_for('dashboard.settings'))
            
            current_user.set_password(new_password)
            db.session.commit()
            flash('Password changed successfully.', 'success')
        
        return redirect(url_for('dashboard.settings'))
    
    return render_template('dashboard/settings.html')


@dashboard_bp.route('/analytics')
@login_required
def analytics():
    """View usage analytics and statistics"""
    # Only available for basic and premium plans
    if current_user.subscription_tier == 'free':
        flash('Analytics are available for Basic and Premium plans only.', 'info')
        return redirect(url_for('subscription.plans'))
    
    # Get date range for analytics
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)  # Last 30 days by default
    
    # Get generations by date
    generations_by_date = db.session.query(
        db.func.date(Generation.timestamp).label('date'),
        db.func.count().label('count')
    ).filter(
        Generation.user_id == current_user.id,
        Generation.timestamp.between(start_date, end_date)
    ).group_by(
        db.func.date(Generation.timestamp)
    ).all()
    
    # Get generations by country
    generations_by_country = db.session.query(
        Generation.country,
        db.func.count().label('count')
    ).filter(
        Generation.user_id == current_user.id
    ).group_by(
        Generation.country
    ).order_by(
        db.desc('count')
    ).limit(10).all()
    
    # Format data for charts
    dates = []
    counts = []
    for date, count in generations_by_date:
        dates.append(date.strftime('%Y-%m-%d'))
        counts.append(count)
    
    countries = []
    country_counts = []
    for country, count in generations_by_country:
        countries.append(country)
        country_counts.append(count)
    
    # Get most viewed/downloaded generations
    most_viewed = Generation.query.filter_by(user_id=current_user.id)\
        .order_by(Generation.view_count.desc())\
        .limit(5)\
        .all()
    
    most_downloaded = Generation.query.filter_by(user_id=current_user.id)\
        .order_by(Generation.download_count.desc())\
        .limit(5)\
        .all()
    
    return render_template('dashboard/analytics.html',
                          dates=dates,
                          counts=counts,
                          countries=countries,
                          country_counts=country_counts,
                          most_viewed=most_viewed,
                          most_downloaded=most_downloaded)