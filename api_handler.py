# File: api_handler.py
import os
import requests
import json
import base64
import re
import time
import sys
import traceback
from aqt import mw
from urllib.request import urlopen
from urllib.parse import unquote
import subprocess

# OpenAI API Endpoints
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

# Debug logging
def debug_log(message):
    """Write debug messages to a separate log file"""
    try:
        addon_dir = os.path.dirname(os.path.abspath(__file__))
        debug_log_path = os.path.join(addon_dir, "debug_log.txt")
        
        with open(debug_log_path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception as e:
        print(f"Failed to write to debug log: {e}")

def extract_image_from_html(html_content):
    """
    Extract image URL from HTML content using regex
    
    Parameters:
    - html_content: HTML content containing an image
    
    Returns:
    - str: Base64 encoded image or None if failed
    """
    try:
        # Use regex to find the img tag and extract the src attribute
        # This pattern looks for src attribute in various formats (with " or ' or no quotes)
        match = re.search(r'<img[^>]+src\s*=\s*(?:["\'](.*?)["\']|(.*?)(?:\s|>))', html_content)
        
        if not match:
            return None
            
        # Get the matched src (either from group 1 or group 2)
        src = match.group(1) if match.group(1) else match.group(2)
        
        if not src:
            return None
            
        # Handle different image formats
        if src.startswith('data:image'):
            # Already a base64 image
            base64_data = src.split(',')[1]
            return base64_data
        elif src.startswith('http'):
            # Remote image URL
            response = urlopen(src)
            image_data = response.read()
            return base64.b64encode(image_data).decode('utf-8')
        else:
            # Local file in Anki media collection
            # Remove any URL encoding
            src = unquote(src)
            # Remove any leading path like "collection.media/"
            src = os.path.basename(src)
            # Get the full path in the media directory
            media_dir = os.path.join(mw.pm.profileFolder(), "collection.media")
            image_path = os.path.join(media_dir, src)
            
            if os.path.exists(image_path):
                with open(image_path, 'rb') as img_file:
                    image_data = img_file.read()
                    return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        print(f"Error extracting image: {e}")
    
    return None

def process_with_openai(api_key, prompt, picture_content=""):
    """
    Process the prompt with OpenAI's API and return the explanation
    
    Parameters:
    - api_key: OpenAI API key
    - prompt: The prompt to send to GPT
    - picture_content: HTML content of the picture field
    
    Returns:
    - str: The explanation from GPT
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Prepare the messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant for Japanese language learners."},
        {"role": "user", "content": prompt}
    ]
    
    data = {
        "model": "gpt-4o",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    try:
        response = requests.post(OPENAI_CHAT_URL, headers=headers, json=data)
        response.raise_for_status()
        
        response_data = response.json()
        if 'choices' in response_data and len(response_data['choices']) > 0:
            explanation = response_data['choices'][0]['message']['content']
            return explanation
        else:
            return None
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

def check_voicevox_running():
    """
    Check if VOICEVOX server is running
    
    Returns:
    - bool: True if VOICEVOX server is running, False otherwise
    """
    try:
        response = requests.get("http://localhost:50021/version")
        return response.status_code == 200
    except:
        return False

def generate_audio(api_key, text):
    """
    Generate audio using VOICEVOX if available
    
    Parameters:
    - api_key: OpenAI API key (not used for VOICEVOX)
    - text: The text to convert to speech
    
    Returns:
    - str: Path to the generated audio file or None if failed
    """
    debug_log("=== AUDIO GENERATION START ===")
    debug_log(f"Text length: {len(text) if text else 'None'}")
    
    try:
        # Check if VOICEVOX is running
        if not check_voicevox_running():
            debug_log("VOICEVOX server is not running. Please start VOICEVOX and try again.")
            return None
        
        # Get the media directory path
        media_dir = os.path.join(mw.pm.profileFolder(), "collection.media")
        debug_log(f"Media directory: {media_dir}")
        
        # Create a unique filename based on content hash and timestamp
        file_hash = base64.b16encode(text.encode()).decode()[:16].lower()
        timestamp = int(time.time())
        filename = f"explanation_audio_{file_hash}_{timestamp}.wav"
        file_path = os.path.join(media_dir, filename)
        debug_log(f"Target file path: {file_path}")

        # SpeakeR ID
        speaker_id = 11

        
        # 1. Create audio query
        debug_log("Creating audio query")
        query_params = {'text': text, 'speaker': speaker_id}  # Use speaker 11 for male voice
        query_response = requests.post('http://localhost:50021/audio_query', params=query_params)
        
        if query_response.status_code != 200:
            debug_log(f"Error in audio_query: {query_response.text}")
            return None
        
        query = query_response.json()
        
        # 2. Generate audio data
        debug_log("Generating audio data")
        synthesis_params = {'speaker': speaker_id}
        synthesis_response = requests.post('http://localhost:50021/synthesis', params=synthesis_params, json=query)
        
        if synthesis_response.status_code != 200:
            debug_log(f"Error in synthesis: {synthesis_response.text}")
            return None
        
        # Save the audio file
        debug_log(f"Writing to file: {file_path}")
        with open(file_path, 'wb') as f:
            f.write(synthesis_response.content)
        
        # Verify the file was written correctly
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            debug_log(f"File successfully written, size: {os.path.getsize(file_path)}")
            debug_log("=== AUDIO GENERATION COMPLETE ===")
            return file_path
        else:
            debug_log("File is empty or doesn't exist")
            return None
            
    except Exception as e:
        debug_log(f"Unexpected error in generate_audio: {str(e)}")
        debug_log(f"Stack trace: {traceback.format_exc()}")
        return None
    finally:
        debug_log("=== AUDIO GENERATION END ===")