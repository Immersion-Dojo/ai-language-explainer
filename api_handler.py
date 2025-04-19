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
import platform

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
    debug_log("=== PROCESS WITH OPENAI START ===")
    debug_log(f"Prompt length: {len(prompt)}")
    
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
        debug_log("Sending request to OpenAI API...")
        response = requests.post(OPENAI_CHAT_URL, headers=headers, json=data, timeout=30)
        debug_log(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            debug_log(f"API returned error status: {response.status_code}")
            debug_log(f"Response text: {response.text[:500]}...")
            return None
            
        response.raise_for_status()
        
        try:
            response_data = response.json()
            debug_log("Successfully parsed JSON response")
        except Exception as e:
            debug_log(f"Error parsing JSON response: {str(e)}")
            debug_log(f"Response text: {response.text[:500]}...")
            return None
            
        if 'choices' in response_data and len(response_data['choices']) > 0:
            explanation = response_data['choices'][0]['message']['content']
            debug_log(f"Received explanation, length: {len(explanation)}")
            debug_log(f"Explanation first 100 chars: {explanation[:100]}...")
            debug_log("=== PROCESS WITH OPENAI COMPLETE ===")
            return explanation
        else:
            debug_log("Response missing 'choices' or empty choices array")
            debug_log(f"Response data: {str(response_data)[:500]}...")
            return None
    except requests.exceptions.Timeout:
        debug_log("Timeout while calling OpenAI API")
        return None
    except requests.exceptions.RequestException as e:
        debug_log(f"Request error calling OpenAI API: {str(e)}")
        return None
    except Exception as e:
        debug_log(f"Unexpected error calling OpenAI API: {str(e)}")
        debug_log(f"Stack trace: {traceback.format_exc()}")
        return None
    finally:
        debug_log("=== PROCESS WITH OPENAI END ===")

def check_voicevox_running():
    """
    Check if VOICEVOX server is running
    
    Returns:
    - bool: True if VOICEVOX server is running, False otherwise
    """
    try:
        debug_log("Checking if VOICEVOX is running...")
        
        # Try multiple URLs to check if VOICEVOX is running
        test_urls = [
            "http://localhost:50021/version",  # Standard URL
            "http://127.0.0.1:50021/version",  # Alternative localhost
            "http://0.0.0.0:50021/version"     # Another alternative
        ]
        
        for url in test_urls:
            try:
                debug_log(f"Trying to connect to VOICEVOX at {url}")
                response = requests.get(url, timeout=1)
                if response.status_code == 200:
                    debug_log(f"VOICEVOX is running at {url}, version: {response.text}")
                    return True
                else:
                    debug_log(f"VOICEVOX at {url} returned non-200 status code: {response.status_code}")
            except requests.exceptions.ConnectionError:
                debug_log(f"VOICEVOX connection error at {url} - server not running")
            except requests.exceptions.Timeout:
                debug_log(f"VOICEVOX connection timeout at {url}")
            except Exception as e:
                debug_log(f"Error checking VOICEVOX at {url}: {str(e)}")
        
        # If we get here, all URLs failed
        debug_log("All VOICEVOX connection attempts failed")
        return False
    except Exception as e:
        debug_log(f"Unexpected error in check_voicevox_running: {str(e)}")
        return False

def get_voicevox_install_instructions():
    """
    Get platform-specific instructions for installing VOICEVOX
    
    Returns:
    - str: Installation instructions
    """
    system = platform.system()
    if system == "Windows":
        return "Download VOICEVOX from https://voicevox.hiroshiba.jp/ and run it before generating audio."
    elif system == "Darwin":  # macOS
        return "Download VOICEVOX from https://voicevox.hiroshiba.jp/ and run it before generating audio. Make sure the VOICEVOX app is running and the API server is enabled in the settings."
    elif system == "Linux":
        return "Install VOICEVOX using Docker or from source: https://github.com/VOICEVOX/voicevox_engine"
    else:
        return "Visit https://voicevox.hiroshiba.jp/ to download VOICEVOX for your platform."

def generate_audio(api_key, text):
    """
    Dispatch to the selected TTS engine and generate audio.
    """
    from . import CONFIG  # import CONFIG here to avoid circular import
    # Determine TTS engine from config (VoiceVox, ElevenLabs, OpenAI TTS)
    engine = CONFIG.get("tts_engine", "VoiceVox")
    if engine == "ElevenLabs":
        return generate_audio_elevenlabs(CONFIG.get("elevenlabs_key", ""), text, CONFIG.get("elevenlabs_voice_id", ""))
    if engine == "OpenAI TTS":
        return generate_audio_openai_tts(api_key, text, CONFIG.get("openai_tts_voice", "alloy"))
    # Fallback to VoiceVox
    debug_log("=== AUDIO GENERATION START (VoiceVox) ===")
    debug_log(f"Text length: {len(text) if text else 'None'}")
    
    # Check for empty text
    if not text or len(text.strip()) == 0:
        debug_log("Empty text provided, cannot generate audio")
        return None
    
    # Limit text length to prevent errors (VOICEVOX has limits)
    max_text_length = 500
    if len(text) > max_text_length:
        debug_log(f"Text too long ({len(text)} chars), truncating to {max_text_length} chars")
        text = text[:max_text_length] + "..."
    
    try:
        # Check if VOICEVOX is running with a very short timeout
        debug_log("Doing a quick check if VOICEVOX is accessible")
        try:
            response = requests.get("http://localhost:50021/version", timeout=1)
            if response.status_code != 200:
                debug_log(f"VOICEVOX not accessible: status code {response.status_code}")
                return None
            debug_log(f"VOICEVOX is accessible, version: {response.text}")
        except Exception as e:
            debug_log(f"VOICEVOX initial check failed: {str(e)}")
            return None
        
        # Get the media directory path
        try:
            media_dir = os.path.join(mw.pm.profileFolder(), "collection.media")
            debug_log(f"Media directory: {media_dir}")
            
            # Check if media directory exists and is writable
            if not os.path.exists(media_dir):
                debug_log(f"Media directory does not exist: {media_dir}")
                try:
                    os.makedirs(media_dir, exist_ok=True)
                    debug_log(f"Created media directory: {media_dir}")
                except Exception as e:
                    debug_log(f"Failed to create media directory: {str(e)}")
                    return None
                    
            # Verify directory is writable with a test file
            test_file_path = os.path.join(media_dir, "voicevox_test.tmp")
            try:
                with open(test_file_path, 'w') as f:
                    f.write("test")
                os.remove(test_file_path)
                debug_log("Media directory is writable")
            except Exception as e:
                debug_log(f"Media directory is not writable: {str(e)}")
                return None
        except Exception as e:
            debug_log(f"Error accessing media directory: {str(e)}")
            return None
        
        # Create a unique filename based on content hash and timestamp
        file_hash = base64.b16encode(text.encode()).decode()[:16].lower()
        timestamp = int(time.time())
        filename = f"explanation_audio_{file_hash}_{timestamp}.wav"
        file_path = os.path.join(media_dir, filename)
        debug_log(f"Target file path: {file_path}")

        # Speaker ID
        speaker_id = 11  # Adjust if needed

        # Set timeout for requests to prevent hanging
        timeout_seconds = 10  # Shorter timeout
        
        # 1. Create audio query
        debug_log("Creating audio query")
        query_params = {'text': text, 'speaker': speaker_id}
        try:
            debug_log(f"Sending audio query request with text: {text[:50]}...")
            query_response = requests.post('http://localhost:50021/audio_query', params=query_params, timeout=timeout_seconds)
            debug_log(f"Audio query response status: {query_response.status_code}")
            debug_log(f"Audio query response content type: {query_response.headers.get('Content-Type', 'unknown')}")
        except requests.exceptions.Timeout:
            debug_log("Timeout while creating audio query")
            return None
        except Exception as e:
            debug_log(f"Error in audio query request: {str(e)}")
            debug_log(f"Stack trace: {traceback.format_exc()}")
            return None
        
        if query_response.status_code != 200:
            debug_log(f"Error in audio_query: {query_response.text[:200]}")
            return None
        
        try:
            query_content = query_response.text
            debug_log(f"Audio query response content (first 50 chars): {query_content[:50]}")
            query = query_response.json()
            debug_log("Successfully parsed audio query JSON response")
        except Exception as e:
            debug_log(f"Error parsing audio query response: {str(e)}")
            debug_log(f"Response content: {query_response.text[:200]}...")
            return None
        
        # 2. Generate audio data
        debug_log("Generating audio data")
        synthesis_params = {'speaker': speaker_id}
        try:
            debug_log("Sending synthesis request...")
            synthesis_response = requests.post('http://localhost:50021/synthesis', params=synthesis_params, json=query, timeout=timeout_seconds)
            debug_log(f"Synthesis response status: {synthesis_response.status_code}")
            debug_log(f"Synthesis response content type: {synthesis_response.headers.get('Content-Type', 'unknown')}")
            debug_log(f"Synthesis response content length: {len(synthesis_response.content)}")
        except requests.exceptions.Timeout:
            debug_log("Timeout while generating audio data")
            return None
        except Exception as e:
            debug_log(f"Error in synthesis request: {str(e)}")
            debug_log(f"Stack trace: {traceback.format_exc()}")
            return None
        
        if synthesis_response.status_code != 200:
            debug_log(f"Error in synthesis: {synthesis_response.text[:200]}")
            return None
            
        if len(synthesis_response.content) < 100:  # Check if response is too small
            debug_log(f"Synthesis response too small, might not be audio: {len(synthesis_response.content)} bytes")
            debug_log(f"Response content (first 100 bytes): {synthesis_response.content[:100]}")
            return None
        
        # Save the audio file
        debug_log(f"Writing to file: {file_path}")
        try:
            with open(file_path, 'wb') as f:
                f.write(synthesis_response.content)
                debug_log(f"Wrote {len(synthesis_response.content)} bytes to file")
            
            # Verify the file was written correctly
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                debug_log(f"File successfully written, size: {file_size} bytes")
                
                if file_size < 100:  # Check if file is too small
                    debug_log("File is too small, might not be valid audio")
                    return None
                    
                debug_log("=== AUDIO GENERATION COMPLETE ===")
                return file_path
            else:
                debug_log("File doesn't exist after writing")
                return None
        except Exception as e:
            debug_log(f"Error writing audio file: {str(e)}")
            debug_log(f"Stack trace: {traceback.format_exc()}")
            return None
            
    except Exception as e:
        debug_log(f"Unexpected error in generate_audio: {str(e)}")
        debug_log(f"Stack trace: {traceback.format_exc()}")
        return None
    finally:
        debug_log("=== AUDIO GENERATION END ===")

# ElevenLabs TTS generation implementation
def generate_audio_elevenlabs(api_key, text, voice_id):
    """Generate audio using ElevenLabs TTS."""
    debug_log("=== ELEVENLABS AUDIO GENERATION START ===")
    if not api_key or not voice_id or not text:
        debug_log("Missing api_key, voice_id, or text for ElevenLabs TTS")
        return None
    try:
        url = f"https://api.elevenlabs.io/v2/voices/{voice_id}/text-to-speech"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }
        payload = {"text": text}
        debug_log(f"Sending ElevenLabs request: voice_id={voice_id}, text length={len(text)}")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        debug_log(f"ElevenLabs status: {response.status_code}")
        if response.status_code != 200:
            debug_log(f"ElevenLabs error: {response.text[:200]}")
            return None
        # Save audio to media directory
        media_dir = os.path.join(mw.pm.profileFolder(), "collection.media")
        os.makedirs(media_dir, exist_ok=True)
        timestamp = int(time.time())
        filename = f"elevenlabs_tts_{voice_id}_{timestamp}.mp3"
        file_path = os.path.join(media_dir, filename)
        with open(file_path, "wb") as f:
            f.write(response.content)
        debug_log(f"Written ElevenLabs audio file: {file_path}")
        return file_path
    except Exception as e:
        debug_log(f"Exception in ElevenLabs TTS: {e}")
        return None
    finally:
        debug_log("=== ELEVENLABS AUDIO GENERATION END ===")

# OpenAI TTS generation implementation
def generate_audio_openai_tts(api_key, text, voice):
    """Generate audio using OpenAI TTS endpoint."""
    debug_log("=== OPENAI TTS GENERATION START ===")
    if not api_key or not text or not voice:
        debug_log("Missing api_key, voice, or text for OpenAI TTS")
        return None
    try:
        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {"model": "tts-1", "voice": voice, "input": text}
        debug_log(f"Sending OpenAI TTS request: model=tts-1, voice={voice}, input length={len(text)}")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        debug_log(f"OpenAI TTS status: {response.status_code}")
        if response.status_code != 200:
            debug_log(f"OpenAI TTS error: {response.text[:200]}")
            return None
        # Save audio to media directory
        media_dir = os.path.join(mw.pm.profileFolder(), "collection.media")
        os.makedirs(media_dir, exist_ok=True)
        timestamp = int(time.time())
        filename = f"openai_tts_{voice}_{timestamp}.mp3"
        file_path = os.path.join(media_dir, filename)
        with open(file_path, "wb") as f:
            f.write(response.content)
        debug_log(f"Written OpenAI TTS audio file: {file_path}")
        return file_path
    except Exception as e:
        debug_log(f"Exception in OpenAI TTS: {e}")
        return None
    finally:
        debug_log("=== OPENAI TTS GENERATION END ===")