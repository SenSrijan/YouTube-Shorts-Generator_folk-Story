
def generate_story_prompt(user_country):

    create_story_prompt = f"""
    Subject: Generate a compelling folk story from {user_country} suitable for a 60-second YouTube Short.

    Goal: To create a concise, visually engaging, and emotionally resonant narrative that captures the essence of {user_country}'s folklore.

    Format:

* Platform: YouTube Shorts (vertical video, 9:16 aspect ratio)
* Duration: 60 seconds maximum.
* Style: Folk tale, legend, or myth.
* Tone: Evocative, engaging, and culturally sensitive.

Specific Requirements:

1. Country Focus:
    * The story MUST originate from and reflect the culture of {user_country}.
    * Incorporate specific cultural elements:
        * Mention a recognizable landmark, natural feature, or traditional object.
        * Include a traditional value, belief, or custom prevalent in the country.
        * If possible include a traditional animal or plant from that country.
2. Narrative Structure (Concise and Engaging):
    * Hook (0-5 seconds): Start with a captivating visual or sound to grab the viewer's attention.
    * Setup (5-20 seconds): Briefly introduce the characters, setting, and the central conflict or mystery.
    * Rising Action/Climax (20-45 seconds): Develop the conflict and build tension towards a pivotal moment.
    * Resolution/Moral (45-60 seconds): Resolve the conflict and deliver a clear moral or lesson, reflecting the cultural values of {user_country}.
3. Visual and Auditory Considerations:
    * Visuals:
        * Describe the visual elements that would accompany the story (e.g., animated illustrations, live-action footage, stock footage, digital art).
        * Suggest a color palette that reflects the mood and culture of the story.
        * Suggest camera movements that would increase the engagement of the short.
    * Audio:
        * Describe the type of music or sound effects that would enhance the storytelling (e.g., traditional instruments, ambient sounds, voiceover narration).
        * Suggest a voice over tone that would be appropiate for the story.
4. Character Development (Simplified):
    * Introduce one or two main characters with distinct traits or roles (e.g., a wise elder, a brave hero, a mischievous spirit).
    * The characters actions should reflect the values of the culture.
5. Story Elements:
    * Include a magical element, a lesson about nature, or a story of courage or wisdom, as appropriate to the folklore of {user_country}.
    * The story should have a clear beginning, middle and end.
6. Cultural Sensitivity:
    * Ensure the story is respectful and accurate in its portrayal of {user_country}'s culture.
    * Avoid stereotypes or misrepresentations.
7. Output:
    * The output should be a detailed story outline, including descriptions of the visuals and audio, that can be used to create a 60-second YouTube Short.
    * Include a short summary of the moral of the story.

Example (Replace with User Input):

"Generate a compelling folk story from Japan suitable for a 60-second YouTube Short. The story should include a Tanuki, and a lesson about respecting nature. The short must be visually engaging, and culturally sensitive."
"""

    return create_story_prompt


def generate_voiceover_prompt(user_story):
    
    script_response = user_story

    voiceover_prompt = f"""
    Subject: Create a Voiceover Script for a Folk Story YouTube Short.

    Goal: To generate a compelling and engaging voiceover script based on the provided folk story, suitable for a 60-second YouTube Short.

    Story to be used:
    {script_response}

    Specific Requirements:

    1.  **Voiceover Style:**
        * The voiceover should be clear, concise, and easy to understand.
        * The tone should be appropriate for a folk story, generally warm, engaging, and slightly dramatic.
        * The pacing should be dynamic, fitting within the 60-second time limit, and matching the visual cues of the story (assuming visuals are being created based on the previous story output).
        * The script should convey the emotions and cultural nuances of the story.
        * If possible, use a tone that reflects the culture from which the story originated.

    2.  **Script Structure:**
        * The script should follow the narrative structure of the provided story (hook, setup, rising action/climax, resolution/moral).
        * Each section of the script should correspond to the appropriate visual and audio elements of the YouTube Short.
        * The script should be timed to fit within the 60-second limit.
        * Use appropriate pauses and emphasis to enhance the storytelling.

    3.  **Language and Delivery:**
        * Use clear and evocative language that is suitable for a wide audience.
        * Pronunciation should be clear and consistent.
        * The script should be written in a way that is easy to read aloud.
        * If the original story contained any specific words from the origin country, try to incorporate those into the voice over, and provide a phonetic pronounciation of those words within parenthesis directly after the word.

    4.  **Emotional Impact:**
        * The voiceover should convey the emotions of the characters and the story's overall message.
        * The delivery should be engaging and captivating, keeping the viewer interested throughout the short.
        * The voiceover should emphasize the moral or lesson of the story.

    5.  **Technical Considerations:**
        * The script should be formatted for easy reading and recording.
    * Provide time cues within the script to indicate when to transition between scenes or emphasize certain points.
    * If possible, give an example of how a certain line should be emphasized, or what type of tone should be used.

    6. **Output:**
        * The output should be a complete voiceover script, formatted for recording, with time cues and notes on delivery.
        * The script should be written in a way that brings the provided folk story to life in a 60-second YouTube Short.
    """
    
    return voiceover_prompt

def generate_voiceover_for_tts_prompt(user_story):
  
    """
    Generate a plain text voiceover script based on the provided folk story,
    suitable for direct input into a text-to-speech API.
    """
    voiceover_prompt = f"""
Subject: Generate a plain text voiceover script for a 60-second folk story YouTube Short.

Goal: Create a voiceover script that is clear, concise, and engaging, written in plain text with natural punctuation and pauses. The script should capture the emotions and cultural nuances of the following folk story and be directly usable as input for a text-to-speech engine.

Story:
{user_story}

Requirements:
1. Write the script in plain text with minimal formatting—only natural punctuation (commas, periods, and line breaks) to indicate pauses.
2. Use a warm, engaging, and slightly dramatic tone.
3. Ensure the script fits within a 60-second read time.
4. Do not include any extra commentary, formatting instructions, or metadata in the output.

Output:
Provide only the final voiceover script in plain text.
"""
    return voiceover_prompt


def generate_scene_prompt(user_story):
    
    story_text = user_story# Assume the model's story output is here.

    image_prompt = f"""
    Subject: Generate Image Generation Prompts for a Folk Story YouTube Short.

    Goal: To create a series of detailed image generation prompts based on the provided folk story, breaking it down scene by scene, for use with a text-to-image generation model.

    Story to be used:
    {story_text}

    Specific Requirements:

    1.  **Scene Breakdown:**
        * Break down the provided folk story into distinct scenes that represent key moments in the narrative.
        * Each scene should correspond to a specific visual element that can be depicted in an image.

    2.  **Image Generation Prompts:**
        * For each scene, create a detailed image generation prompt that includes:
        * **Subject:** Describe the main subject of the image (characters, objects, landscapes).
        * **Setting:** Describe the environment or background of the image.
        * **Composition:** Describe the composition of the image (camera angle, framing, perspective).
        * **Style:** Specify the desired art style (e.g., watercolor, digital painting, realistic, stylized, folk art, animation still).
        * **Lighting:** Describe the lighting conditions (e.g., warm sunlight, moonlight, dramatic shadows).
        * **Color Palette:** Suggest a color palette that reflects the mood and culture of the story.
        * **Emotion/Mood:** Describe the desired emotion or mood of the image.
        * **Specific Details:** Include any specific details that are essential to the scene (e.g., facial expressions, gestures, clothing, objects).
        * **Cultural Elements:** Ensure the prompts reflect the cultural elements described in the original story.
    * Prompts should be detailed and specific to ensure accurate image generation.
    * Prompts should be written to create vertical images, suitable for a YouTube short.

3.  **Scene Sequence:**
    * The image generation prompts should be presented in the correct sequence to tell the story visually.
    * Each prompt should be numbered to indicate its position in the sequence.

4.  **Cultural Accuracy:**
    * Ensure the prompts accurately reflect the cultural elements of the original story.
    * Avoid stereotypes or misrepresentations.

5.  **Output:**
    * The output should be a numbered list of detailed image generation prompts, one for each scene in the story.
    * Each prompt should be formatted for easy use with a text-to-image generation model.
    * Each prompt should be self contained, and require no outside context.

Example of a scene prompt:

"Scene 1: A young girl with bright, curious eyes, wearing traditional clothing from [Country], stands at the edge of a lush, green forest. The sun filters through the trees, creating a warm, golden glow. Style: Digital painting, with a soft, painterly feel. Color palette: Warm greens, yellows, and browns. Mood: Peaceful and serene. Composition: Close-up shot of the girl, with the forest in the background. Lighting: Soft, diffused sunlight."
"""

    return image_prompt



def get_image_prompt_dict(image_gen_prompts):
    
    prompt = f"""You are provided with a series of image generation scenes formatted 
    as shown below. Your task is to convert this text into a Python dictionary where:
    Each key is the scene ID (for example, "Scene 1", "Scene 2", etc.).
    The corresponding value is a dictionary with a single key "Prompt" that holds the exact image generation prompt text. This text is what follows after the - **Image Prompt:** label in each scene.
    Output only the valid Python dictionary code without any additional commentary.
    Here is the input text: {image_gen_prompts}"""

    return prompt

   