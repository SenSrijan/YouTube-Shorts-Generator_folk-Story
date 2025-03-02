from flask import Blueprint, jsonify, request, current_app, send_from_directory
from models import db, User, Generation
from auth import api_key_required
from generator import YouTubeShortsGenerator
from prompts import get_image_prompt_dict
from llm_integration import call_llm_gorq
import os
import logging
import json
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
logger = logging.getLogger(__name__)

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Basic API health check endpoint"""
    return jsonify({
        'status': 'ok',
        'version': '1.0.0'
    })

@api_bp.route('/generate', methods=['POST'])
@api_key_required
def generate_content(user):
    """Generate YouTube Shorts content via API"""
    try:
        # Check if user can generate more content
        if not user.can_generate():
            return jsonify({
                'status': 'error',
                'message': f'Monthly generation limit reached for your {user.subscription_tier} plan'
            }), 403
        
        # Parse request data
        data = request.get_json(force=True)
        country = data.get('country', '').strip()
        
        if not country:
            return jsonify({
                'status': 'error',
                'message': 'Country name is required'
            }), 400
        
        # Initialize generator
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
            file_paths = generator.save_outputs(current_app.config['OUTPUT_FOLDER'])
        except Exception as e:
            logger.exception("Error saving generated outputs:")
            return jsonify({
                'status': 'error',
                'message': 'Failed to save outputs'
            }), 500
        
        # Record generation in database
        new_generation = Generation(
            generation_id=generator.generation_id,
            user_id=user.id,
            country=country,
            story_path=file_paths['story_path'],
            voiceover_path=file_paths['voiceover_path'],
            voiceover_tts_path=file_paths['voiceover_tts_path'],
            scenes_path=file_paths['scenes_path']
        )
        
        db.session.add(new_generation)
        
        # Update user's generation count
        user.increment_generation_count()
        db.session.commit()
        
        # Prepare response
        response_data = {
            'status': 'success',
            'message': f'YouTube Short content for {country} generated successfully',
            'generation_id': generator.generation_id,
            'paths': file_paths,
            'content': {
                'story': results['story'],
                'voiceover': results['voiceover'],
                'scenes': results['scenes']
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.exception("Error in API generate endpoint:")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/generations', methods=['GET'])
@api_key_required
def list_generations(user):
    """List all generations for the authenticated user"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Limit per_page to prevent abuse
        per_page = min(per_page, 50)
        
        # Filter parameters
        country = request.args.get('country', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Build query
        query = Generation.query.filter_by(user_id=user.id)
        
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
        
        # Execute query with pagination
        pagination = query.order_by(Generation.timestamp.desc()).paginate(page=page, per_page=per_page)
        
        # Format results
        generations = []
        for generation in pagination.items:
            generations.append({
                'id': generation.id,
                'generation_id': generation.generation_id,
                'country': generation.country,
                'timestamp': generation.timestamp.isoformat(),
                'view_count': generation.view_count,
                'download_count': generation.download_count,
                'files': {
                    'story_path': generation.story_path,
                    'voiceover_path': generation.voiceover_path,
                    'voiceover_tts_path': generation.voiceover_tts_path,
                    'scenes_path': generation.scenes_path
                }
            })
        
        return jsonify({
            'status': 'success',
            'page': page,
            'per_page': per_page,
            'total_pages': pagination.pages,
            'total_items': pagination.total,
            'generations': generations
        })
        
    except Exception as e:
        logger.exception("Error in API list generations endpoint:")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/generation/<generation_id>', methods=['GET'])
@api_key_required
def get_generation(user, generation_id):
    """Get details for a specific generation"""
    try:
        generation = Generation.query.filter_by(
            generation_id=generation_id,
            user_id=user.id
        ).first()
        
        if not generation:
            return jsonify({
                'status': 'error',
                'message': 'Generation not found'
            }), 404
        
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
            logger.exception("Error loading content files:")
            content = {
                'story': 'Content not available',
                'voiceover': 'Content not available',
                'scenes': 'Content not available',
                'metadata': {}
            }
        
        return jsonify({
            'status': 'success',
            'generation': {
                'id': generation.id,
                'generation_id': generation.generation_id,
                'country': generation.country,
                'timestamp': generation.timestamp.isoformat(),
                'view_count': generation.view_count,
                'download_count': generation.download_count,
                'files': {
                    'story_path': generation.story_path,
                    'voiceover_path': generation.voiceover_path,
                    'voiceover_tts_path': generation.voiceover_tts_path,
                    'scenes_path': generation.scenes_path
                },
                'content': content
            }
        })
        
    except Exception as e:
        logger.exception("Error in API get generation endpoint:")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@api_bp.route('/download/<generation_id>/<file_type>', methods=['GET'])
@api_key_required
def download_file(user, generation_id, file_type):
    """Download files associated with a generation"""
    generation = Generation.query.filter_by(
        generation_id=generation_id,
        user_id=user.id
    ).first()
    
    if not generation:
        return jsonify({
            'status': 'error',
            'message': 'Generation not found'
        }), 404
    
    # Map file types to file paths
    file_paths = {
        'story': ('story.txt', os.path.join('outputs', generation_id, 'story.txt')),
        'voiceover': ('voiceover.txt', os.path.join('outputs', generation_id, 'voiceover.txt')),
        'audio': ('voiceover_tts.mp3', os.path.join('outputs', generation_id, 'voiceover_tts.mp3')),
        'scenes': ('scenes.txt', os.path.join('outputs', generation_id, 'scenes.txt'))
    }
    
    if file_type not in file_paths:
        return jsonify({
            'status': 'error',
            'message': 'Invalid file type requested'
        }), 400
    
    # Increment download count
    generation.download_count += 1
    db.session.commit()
    
    filename, path = file_paths[file_type]
    
    try:
        return send_from_directory(
            current_app.config['OUTPUT_FOLDER'],
            path,
            download_name=filename,
            as_attachment=True
        )
    except Exception as e:
        logger.exception("Error downloading file:")
        return jsonify({
            'status': 'error',
            'message': 'File not found'
        }), 404

@api_bp.route('/user/usage', methods=['GET'])
@api_key_required
def get_usage(user):
    """Get current user's usage statistics"""
    try:
        # Get current plan details
        plan_limits = {
            'free': 3,
            'basic': 30,
            'premium': float('inf')  # Unlimited
        }
        
        limit = plan_limits.get(user.subscription_tier, 0)
        usage_percent = (user.monthly_generations / limit * 100) if limit != float('inf') else 0
        
        # Get counts of generations
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_generations_count = Generation.query.filter(
            Generation.user_id == user.id,
            Generation.timestamp >= month_start
        ).count()
        
        return jsonify({
            'status': 'success',
            'usage': {
                'subscription_tier': user.subscription_tier,
                'subscription_status': user.subscription_status,
                'monthly_limit': 'Unlimited' if limit == float('inf') else limit,
                'monthly_used': user.monthly_generations,
                'usage_percent': usage_percent,
                'remaining': 'Unlimited' if limit == float('inf') else (limit - user.monthly_generations),
                'total_generations': user.total_generations,
                'month_generations': month_generations_count
            }
        })
        
    except Exception as e:
        logger.exception("Error in API usage endpoint:")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500