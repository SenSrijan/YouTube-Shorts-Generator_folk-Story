from flask import Flask, render_template, request, jsonify, send_from_directory
import logging
import os
import json
from generator import YouTubeShortsGenerator
from prompts import get_image_prompt_dict
from llm_integration import call_llm_gorq  # Ensure correct function import

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask app configuration
app = Flask(__name__)
#app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
#if not app.config['SECRET_KEY']:
    #raise ValueError("Error: SECRET_KEY is not set in the environment.")

app.config['OUTPUT_FOLDER'] = 'static/outputs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Ensure output directory exists and is writable
try:
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
except Exception as e:
    logger.error(f"Failed to create output directory: {e}")
    raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
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
    try:
        return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        logger.exception("Error in file download:")
        return jsonify({"error": "File not found."}), 404

@app.route('/history')
def history():
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
