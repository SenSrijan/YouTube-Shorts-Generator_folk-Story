import os
import json
import logging
from datetime import datetime
from llm_integration import call_llm,call_llm_gorq
from generate_voiceover import text_to_speech
import ast  # To safely convert the LLM’s output string to a dictionary
#from flux_image_generator import YouTubeShortsImageGenerator
from prompts import get_image_prompt_dict
import re




logger = logging.getLogger(__name__)

class YouTubeShortsGenerator:
    """Handles the generation of folk story YouTube Shorts content, including voiceover TTS conversion."""
    
    def __init__(self):
        self.country_name = ""
        self.story_content = ""
        self.voiceover_script = ""
        self.voiceover_tts_path = ""  # Path to the TTS-generated audio file
        self.scene_prompts = ""
        self.images = {} 
        self.generation_id = ""
        
    def set_country(self, country: str) -> None:
        """Set the country and generate a unique ID for this generation."""
        self.country_name = country.strip()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.generation_id = f"{self.country_name.lower().replace(' ', '_')}_{timestamp}"
    
    def _create_story_prompt(self) -> str:
        # Your existing implementation to generate the story prompt based on self.country_name
        # For example:
        return f"Generate a compelling folk story from {self.country_name} suitable for a 60-second YouTube Short."
    
    def _create_voiceover_prompt(self) -> str:
        # Your existing implementation to create the voiceover prompt based on self.story_content
        return f"Create a voiceover script for the following folk story (to be read in plain text for TTS):\n\n{self.story_content}"
    
    def _create_scene_prompt(self) -> str:
        # Your existing implementation to create the scene prompt based on self.story_content
        return f"Break down the following folk story into numbered scenes with detailed image prompts:\n\n{self.story_content}"
    
    def generate_story(self) -> str:
        """Generate the folk story."""
        logger.info("Generating folk story for %s", self.country_name)
        response = call_llm_gorq(self._create_story_prompt())
        self.story_content = response.strip()
        if not self.story_content:
            error_msg = "Failed to generate story content."
            logger.error(error_msg)
            raise ValueError(error_msg)
        logger.info("Story generation completed")
        return self.story_content

    def generate_voiceover(self) -> str:
        """Generate the voiceover script and convert it to speech using TTS."""
        if not self.story_content:
            raise ValueError("Story content must be generated first.")
        
        logger.info("Generating voiceover script")
        response = call_llm_gorq(self._create_voiceover_prompt())
        self.voiceover_script = response.strip()
        if not self.voiceover_script:
            error_msg = "Failed to generate voiceover script."
            logger.error(error_msg)
            raise ValueError(error_msg)
        logger.info("Voiceover script generation completed")
        
        # Generate TTS audio from the voiceover script
        voice_rss_api_key = os.getenv("VOICE_RSS_API_KEY")
        if not voice_rss_api_key:
            raise ValueError("VOICE_RSS_API_KEY is not set")
        
        # Determine output path for the TTS audio file
        gen_dir = os.path.join("static", "outputs", self.generation_id)
        os.makedirs(gen_dir, exist_ok=True)
        tts_output_path = os.path.join(gen_dir, "voiceover_tts.mp3")
        
        # Call the TTS function (make sure text_to_speech accepts an output_file parameter)
        text_to_speech(self.voiceover_script, voice_rss_api_key, output_file=tts_output_path)
        
        self.voiceover_tts_path = f"/static/outputs/{self.generation_id}/voiceover_tts.mp3"
        logger.info("Voiceover TTS audio generated at %s", self.voiceover_tts_path)
        
        return self.voiceover_script

    def generate_scene_prompts(self) -> str:
        """Generate image prompts for each scene."""
        if not self.story_content:
            raise ValueError("Story content must be generated first.")
        
        logger.info("Generating scene image prompts")
        response = call_llm_gorq(self._create_scene_prompt())
        self.scene_prompts = response.strip()
        if not self.scene_prompts:
            error_msg = "Failed to generate scene prompts."
            logger.error(error_msg)
            raise ValueError(error_msg)
        logger.info("Scene prompt generation completed")
        return self.scene_prompts
    
    def generate_images(self) -> dict:
        """Generate images for each scene using Flux image generator."""
        if not self.scene_prompts:
            raise ValueError("Scene prompts must be generated first.")
    
        # Convert scene prompts text to a dictionary using LLM
        image_prompt_conversion = call_llm_gorq(get_image_prompt_dict(self.scene_prompts)).strip()
        # Remove "python" if it's at the start of the response
        image_prompt_intermediate = image_prompt_conversion.removeprefix("```python")
        image_prompt_final = image_prompt_intermediate.removesuffix("```")
        

        print(image_prompt_final)
        try:
            scene_dict = ast.literal_eval(image_prompt_final)
        except Exception as e:
            raise ValueError("Failed to convert scene prompts to dictionary: " + str(e))
    
        #image_generator = YouTubeShortsImageGenerator()
        self.images = {}
    
        # Create generation output directory
        gen_dir = os.path.join("static", "outputs", self.generation_id)
        os.makedirs(gen_dir, exist_ok=True)
    
        for scene_id, prompt_obj in scene_dict.items():
            prompt_text = prompt_obj.get("Prompt")
            if prompt_text:
                # Generate image using flux_image_generator
                #image = image_generator.generate_image(prompt_text)
                # Save image file with a unique name based on scene id
                image_filename = f"{scene_id.replace(' ', '_').lower()}.png"
                image_path = os.path.join(gen_dir, image_filename)
                #image.save(image_path)
                self.images[scene_id] = f"/outputs/{self.generation_id}/{image_filename}"
    
        logger.info("Image generation completed")
        return self.images


    def generate_all(self) -> dict:
        """Generate all components of the YouTube Short."""
        self.generate_story()
        self.generate_voiceover()
        self.generate_scene_prompts()
        #self.generate_images()   # Generate images for each scene
        return {
            "country": self.country_name,
            "generation_id": self.generation_id,
            "story": self.story_content,
            "voiceover": self.voiceover_script,
            "voiceover_tts": self.voiceover_tts_path,
            "scenes": self.scene_prompts
            #"images": self.images   # Include the images in the output
        }

    def save_outputs(self, output_dir: str) -> dict:
        """Save all generated content to files and return their paths."""
        gen_dir = os.path.join(output_dir, self.generation_id)
        os.makedirs(gen_dir, exist_ok=True)
        try:
            # Save story
            story_path = os.path.join(gen_dir, "story.txt")
            with open(story_path, "w", encoding="utf-8") as f:
                f.write(self.story_content)
            # Save voiceover script
            voiceover_path = os.path.join(gen_dir, "voiceover.txt")
            with open(voiceover_path, "w", encoding="utf-8") as f:
                f.write(self.voiceover_script)
            # Save scene prompts
            scenes_path = os.path.join(gen_dir, "scenes.txt")
            with open(scenes_path, "w", encoding="utf-8") as f:
                f.write(self.scene_prompts)
            # Create metadata file
            metadata = {
                    "country": self.country_name,
                    "generation_id": self.generation_id,
                    "timestamp": datetime.now().isoformat(),
                    "files": {
                        "story": story_path,
                        "voiceover": voiceover_path,
                        "voiceover_tts": os.path.join(gen_dir, "voiceover_tts.mp3"),
                        "scenes": scenes_path,
                        "images": self.images   # New field for images
                        }
                    }
            metadata_path = os.path.join(gen_dir, "metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
                
            logger.info("All outputs saved to %s", gen_dir)
            return {
                "generation_id": self.generation_id,
                "story_path": f"/outputs/{self.generation_id}/story.txt",
                "voiceover_path": f"/outputs/{self.generation_id}/voiceover.txt",
                "voiceover_tts_path": f"/outputs/{self.generation_id}/voiceover_tts.mp3",
                "scenes_path": f"/outputs/{self.generation_id}/scenes.txt",
                "metadata_path": f"/outputs/{self.generation_id}/metadata.json"
            }
        except Exception as e:
            logger.exception("Error saving outputs:")
            raise
