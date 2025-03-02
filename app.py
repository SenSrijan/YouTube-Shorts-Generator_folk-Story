from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash
from flask_login import LoginManager, current_user
import logging
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

# Import modules from original application
from generator import YouTubeShortsGenerator
from prompts import get_image_prompt_dict
from llm_integration import call_llm_gorq

# Import SaaS components
from models import db, User, Generation, ApiKey, SubscriptionPlan, PaymentHistory
from auth import auth_bp, init_login_manager
from subscription import sub_bp, init_stripe, initialize_plans
from dashboard import dashboard_bp
from api import api_bp
from email_service import send_welcome_email, send_generation_completion_notification

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    # Flask app configuration
    app = Flask(__name__)
    
    # Configuration settings
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///shorts_generator.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['OUTPUT_FOLDER'] = 'static/outputs'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
    
    # Email configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@youtubeshortsgen.com')
    
    # Stripe configuration
    app.config['STRIPE_SECRET_KEY'] = os.getenv('STRIPE_SECRET_KEY')
    app.config['STRIPE_PUBLISHABLE_KEY'] = os.getenv('STRIPE_PUBLISHABLE_KEY')
    app.config['STRIPE_WEBHOOK_SECRET'] = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    # Initialize extensions
    db.init_app(app)
    init_login_manager(app)
    init_stripe(app)
    
    # Ensure output directory exists
    try:
        os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create output directory: {e}")
        raise
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(sub_bp, url_prefix='/subscription')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(api_bp)
    
    # Background tasks scheduler
    scheduler = BackgroundScheduler()
    
    @scheduler.scheduled_job('cron', day=1, hour=0, minute=0)
    def reset_monthly_counters():
        """Reset monthly generation counters on the first day of each month"""
        with app.app_context():
            users = User.query.all()
            for user in users:
                user.monthly_generations = 0
            db.session.commit()
            logger.info("Monthly generation counters reset")
    
    @scheduler.scheduled_job('cron', day='*', hour=0, minute=0)
    def reset_daily_api_usage():
        """Reset daily API request counters"""
        with app.app_context():
            api_keys = ApiKey.query.all()
            for key in api_keys:
                key.daily_requests = 0
            db.session.commit()
            logger.info("Daily API request counters reset")
            
    # Start scheduler
    scheduler.start()
    
    # Main routes
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return render_template('index.html')
    
    @app.route('/generate', methods=['POST'])
    def generate():
        """Legacy endpoint for backward compatibility"""
        # If user is authenticated, track usage
        if current_user.is_authenticated:
            # Check if user can generate more content
            if not current_user.can_generate():
                flash(f'You have reached your monthly generation limit for the {current_user.subscription_tier} plan.', 'error')
                return jsonify({"error": "Monthly generation limit reached."}), 403
                
            # Increment usage counter
            current_user.increment_generation_count()
        
        try:
            data = request.get_json(force=True)
            country = data.get('country', '').strip()
            if not country:
                return jsonify({"error": "Country name is required."}), 400
                
            generator = YouTubeShortsGenerator()
            generator.set_country(country)
            
            # Generate all outputs
            results = generator.generate_all()
            
            # Generate scene image prompts
            try:
                scene_prompts = call_llm_gorq(get_image_prompt_dict(results["scenes"]))
                if "Error" in scene_prompts:
                    logger.warning("LLM returned an error for scene generation")
                    scene_prompts = "Scene generation failed."
                results["scenes"] = scene_prompts
            except Exception as e:
                logger.exception("Error generating scenes via LLM:")
                results["scenes"] = "Scene generation error."
                
            # Save outputs
            try:
                file_paths = generator.save_outputs(app.config['OUTPUT_FOLDER'])
            except Exception as e:
                logger.exception("Error saving generated outputs:")
                return jsonify({"error": "Failed to save outputs."}), 500
                
            # If user is authenticated, record the generation
            if current_user.is_authenticated:
                new_generation = Generation(
                    generation_id=generator.generation_id,
                    user_id=current_user.id,
                    country=country,
                    story_path=file_paths['story_path'],
                    voiceover_path=file_paths['voiceover_path'],
                    voiceover_tts_path=file_paths['voiceover_tts_path'],
                    scenes_path=file_paths['scenes_path']
                )
                db.session.add(new_generation)
                db.session.commit()
                
                # Send notification email (async in production)
                send_generation_completion_notification(
                    current_user.email,
                    current_user.username,
                    country,
                    generator.generation_id
                )
                
            response_data = {
                "status": "success",
                "message": f"YouTube Short content for {country} generated successfully.",
                "generation_id": generator.generation_id,
                "paths": file_paths,
                "preview": {
                    "story_preview": results["story"][:300] + "..." if len(results["story"]) > 300 else results["story"],
                    "voiceover_preview": results["voiceover"][:300] + "..." if len(results["voiceover"]) > 300 else results["voiceover"],
                    "voiceover_tts_preview": "Voiceover TTS audio is ready. Click the download button to listen.",
                    "scenes_preview": results["scenes"][:300] + "..." if len(results["scenes"]) > 300 else results["scenes"]
                }
            }
            
            response_data_test = {
                "status": "success",
                "message": f"YouTube Short content for {country} generated successfully.",
                "generation_id": generator.generation_id,
                "paths": file_paths,
                "preview": {
                    "story_preview": results["story"],
                    "voiceover_preview": results["voiceover"],
                    "voiceover_tts_preview": "Voiceover TTS audio is ready. Click the download button to listen.",
                    "scenes_preview": results["scenes"]
                }
            }
            return jsonify(response_data_test)
            
        except Exception as e:
            logger.exception("Error in /generate endpoint:")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/outputs/<path:filename>')
    def download_file(filename):
        """Legacy endpoint for backward compatibility"""
        try:
            # If user is authenticated, track the download
            if current_user.is_authenticated:
                # Extract generation_id from the path
                # Assuming path format is: outputs/{generation_id}/file.ext
                parts = filename.split('/')
                if len(parts) >= 2:
                    generation_id = parts[0]
                    generation = Generation.query.filter_by(
                        generation_id=generation_id,
                        user_id=current_user.id
                    ).first()
                    
                    if generation:
                        generation.download_count += 1
                        db.session.commit()
                
            return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)
        except Exception as e:
            logger.exception("Error in file download:")
            return jsonify({"error": "File not found."}), 404
    
    @app.route('/history')
    def history():
        """Legacy endpoint for backward compatibility"""
        # Redirect to new dashboard if user is authenticated
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.generations'))
            
        # For non-authenticated users, fallback to the original behavior
        try:
            history_data = []
            for root, dirs, files in os.walk(app.config['OUTPUT_FOLDER']):
                for dir_name in dirs:
                    metadata_path = os.path.join(app.config['OUTPUT_FOLDER'], dir_name, "metadata.json")
                    if os.path.exists(metadata_path):
                        with open(metadata_path, 'r', encoding="utf-8") as f:
                            metadata = json.load(f)
                            history_data.append(metadata)
            history_data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return render_template('history.html', history=history_data)
        except Exception as e:
            logger.exception("Error loading history:")
            return render_template('history.html', history=[], error=str(e))
    
    @app.route('/view/<generation_id>')
    def view_generation(generation_id):
        """Legacy endpoint for backward compatibility"""
        # Redirect to new dashboard if user is authenticated
        if current_user.is_authenticated:
            # Check if this generation belongs to the user
            generation = Generation.query.filter_by(
                generation_id=generation_id,
                user_id=current_user.id
            ).first()
            
            if generation:
                return redirect(url_for('dashboard.view_generation', generation_id=generation_id))
                
        # For non-authenticated users or other generations, fallback to original behavior
        try:
            gen_dir = os.path.join(app.config['OUTPUT_FOLDER'], generation_id)
            metadata_path = os.path.join(gen_dir, "metadata.json")
            if not os.path.exists(metadata_path):
                return render_template('error.html', message="Generation not found")
                
            with open(metadata_path, 'r', encoding="utf-8") as f:
                metadata = json.load(f)
                
            with open(os.path.join(gen_dir, "story.txt"), 'r', encoding="utf-8") as f:
                story = f.read()
            with open(os.path.join(gen_dir, "voiceover.txt"), 'r', encoding="utf-8") as f:
                voiceover = f.read()
            with open(os.path.join(gen_dir, "scenes.txt"), 'r', encoding="utf-8") as f:
                scenes = f.read()
                
            return render_template('view.html', 
                                metadata=metadata, 
                                story=story, 
                                voiceover=voiceover, 
                                scenes=scenes,
                                generation_id=generation_id)
                                
        except Exception as e:
            logger.exception("Error viewing generation:")
            return render_template('error.html', message=f"Error: {str(e)}")
            
    @app.context_processor
    def inject_user_data():
        """Inject common data into all templates"""
        data = {
            'app_name': 'YouTube Shorts Generator',
            'current_year': datetime.utcnow().year
        }
        
        if current_user.is_authenticated:
            data['user_tier'] = current_user.subscription_tier
            
            # Calculate days left in subscription
            if current_user.subscription_expiry:
                days_left = (current_user.subscription_expiry - datetime.utcnow()).days
                data['subscription_days_left'] = max(0, days_left)
                
            # Get plan info
            plan = SubscriptionPlan.query.filter_by(name=current_user.subscription_tier).first()
            if plan:
                data['plan_limit'] = plan.monthly_generations
                if plan.monthly_generations > 0:
                    data['usage_percent'] = min(100, (current_user.monthly_generations / plan.monthly_generations) * 100)
                else:
                    data['usage_percent'] = 100
                    
        return data
        
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html', message="Page not found"), 404
        
    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', message="Internal server error"), 500
        
    # Initialize database and subscription plans on first run
    with app.app_context():
        db.create_all()
        initialize_plans()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)