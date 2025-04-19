# File: __init__.py
from aqt import mw, gui_hooks
from aqt.utils import qconnect, showInfo, tooltip, askUser
from aqt.qt import QAction, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QLineEdit, QTextEdit, QProgressDialog, QCheckBox, QMessageBox, QApplication, Qt, QTimer, QMenu, QWidget
from anki.notes import Note
import os
import json
import threading
import time
import sys
import subprocess
import traceback
import atexit
import platform
from aqt.browser import Browser
import requests

# Set up crash handler
def setup_crash_handler():
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    crash_log_path = os.path.join(addon_dir, "crash_log.txt")
    
    def log_system_info():
        try:
            with open(crash_log_path, "a", encoding="utf-8") as f:
                f.write(f"\n\n=== SYSTEM INFO [{time.strftime('%Y-%m-%d %H:%M:%S')}] ===\n")
                f.write(f"Platform: {platform.platform()}\n")
                f.write(f"Python: {sys.version}\n")
                f.write(f"Anki version: {mw.pm.meta.get('version', 'unknown')}\n")
                
                # Try to get Qt version
                try:
                    from aqt.qt import QT_VERSION_STR
                    f.write(f"Qt version: {QT_VERSION_STR}\n")
                except:
                    f.write("Qt version: unknown\n")
                    
                f.write("=== END SYSTEM INFO ===\n\n")
        except Exception as e:
            print(f"Failed to log system info: {e}")
    
    # Register the exit handler
    atexit.register(log_system_info)
    
    # Log initial system info
    log_system_info()

# Run crash handler setup
setup_crash_handler()

# Check for required dependencies
def check_dependencies():
    try:
        import requests
    except ImportError:
        # Show a message about installing dependencies
        tooltip("Installing required dependencies for GPT Explainer addon...")
        
        # Get the addon directory
        addon_dir = os.path.dirname(os.path.abspath(__file__))
        requirements_path = os.path.join(addon_dir, "requirements.txt")
        
        # Install dependencies using pip
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])
        
        # Show success message
        tooltip("Dependencies installed successfully!")

# Run dependency check
check_dependencies()

# Now import the module that requires these dependencies
from .api_handler import process_with_openai, generate_audio, check_voicevox_running, get_voicevox_install_instructions

# Set up logging
def log_error(message, error=None):
    """Log error messages to a file for debugging"""
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(addon_dir, "error_log.txt")
    
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
            if error:
                f.write(f"Error details: {str(error)}\n")
                f.write(traceback.format_exc())
                f.write("\n" + "-"*50 + "\n")
    except Exception as e:
        print(f"Failed to write to log file: {e}")

# Global variables to store configuration
CONFIG = {
    "note_type": "",
    "word_field": "",
    "sentence_field": "",
    "definition_field": "",
    "explanation_field": "",
    "explanation_audio_field": "",
    "openai_key": "",
    "gpt_prompt": "Please write a short explanation of the word '{word}' in the context of the original sentence: '{sentence}'. The definition of the word is: '{definition}'. Write an explanation that helps a Japanese beginner understand the word and how it is used with this context as an example. Explain it in the same way a native would explain it to a child. Don't use any English, only use simpler Japanese. Don't write the furigana for any of the words in brackets after the word. Don't start with stuff like \u3068\u3044\u3046\u8a00\u8449\u3092\u7c21\u5358\u306b\u8aac\u660e\u3059\u308b\u306d, just dive straight into explaining after starting with the word.",
    "tts_engine": "OpenAI TTS",
    "elevenlabs_key": "",
    "elevenlabs_voice_id": "",
    "openai_tts_voice": "alloy"
}

# Load configuration
def load_config():
    global CONFIG
    # Load default values from meta.json
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    defaults = {}
    try:
        with open(os.path.join(addon_dir, "meta.json"), encoding="utf-8") as mf:
            meta = json.load(mf)
            defaults = meta.get("config", {}) or {}
    except Exception:
        pass
    # Load user config
    user = mw.addonManager.getConfig(__name__) or {}
    # Backward compatibility mapping for old key names
    rename_map = {
        "explaination_field": "explanation_field",
        "explaination_audio_field": "explanation_audio_field",
        "elevenlabs_api_key": "elevenlabs_key"
    }
    for old_key, new_key in rename_map.items():
        if old_key in user and new_key not in user:
            user[new_key] = user.pop(old_key)
    # Merge defaults and user overrides without blanking defaults
    for key, defval in defaults.items():
        if key in user:
            if isinstance(defval, str):
                # Use user value only if non-empty, else fallback to default
                CONFIG[key] = user[key] if user[key] else defval
            else:
                CONFIG[key] = user[key]
        else:
            CONFIG[key] = defval
    # Include any extra user-only keys
    for key, val in user.items():
        if key not in defaults:
            CONFIG[key] = val
    log_error(f"Final merged config: {CONFIG}")

# Save configuration
def save_config():
    mw.addonManager.writeConfig(__name__, CONFIG)

# Get all available note types
def get_note_types():
    # Updated for Anki 25+
    return [nt['name'] for nt in mw.col.models.all()]

# Get all fields for a specific note type
def get_fields_for_note_type(note_type_name):
    # Updated for Anki 25+
    model = None
    for nt in mw.col.models.all():
        if nt['name'] == note_type_name:
            model = nt
            break
    
    if not model:
        return []
    
    return [field['name'] for field in model['flds']]

# Configuration dialog
class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super(ConfigDialog, self).__init__(parent)
        self.setWindowTitle("GPT Language Explainer Settings")
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # =====================
        # Note & Field Configuration
        # =====================
        layout.addWidget(QLabel("<b>Note & Field Configuration</b>"))
        # Note Type selection
        note_type_layout = QHBoxLayout()
        note_type_layout.addWidget(QLabel("Note Type:"))
        self.note_type_combo = QComboBox()
        self.note_type_combo.addItems(get_note_types())
        qconnect(self.note_type_combo.currentIndexChanged, self.update_field_combos)
        note_type_layout.addWidget(self.note_type_combo)
        layout.addLayout(note_type_layout)
        # Field selection combos
        word_field_layout = QHBoxLayout()
        word_field_layout.addWidget(QLabel("Word Field:"))
        self.word_field_combo = QComboBox()
        word_field_layout.addWidget(self.word_field_combo)
        layout.addLayout(word_field_layout)
        sentence_field_layout = QHBoxLayout()
        sentence_field_layout.addWidget(QLabel("Sentence Field:"))
        self.sentence_field_combo = QComboBox()
        sentence_field_layout.addWidget(self.sentence_field_combo)
        layout.addLayout(sentence_field_layout)
        definition_field_layout = QHBoxLayout()
        definition_field_layout.addWidget(QLabel("Definition Field:"))
        self.definition_field_combo = QComboBox()
        definition_field_layout.addWidget(self.definition_field_combo)
        layout.addLayout(definition_field_layout)
        explanation_field_layout = QHBoxLayout()
        explanation_field_layout.addWidget(QLabel("Explanation Field:"))
        self.explanation_field_combo = QComboBox()
        explanation_field_layout.addWidget(self.explanation_field_combo)
        layout.addLayout(explanation_field_layout)
        audio_field_layout = QHBoxLayout()
        audio_field_layout.addWidget(QLabel("Explanation Audio Field:"))
        self.explanation_audio_field_combo = QComboBox()
        audio_field_layout.addWidget(self.explanation_audio_field_combo)
        layout.addLayout(audio_field_layout)
        # Verification label for field selection
        self.field_verification_label = QLabel()
        layout.addWidget(self.field_verification_label)

        # =====================
        # Text Generation
        # =====================
        layout.addWidget(QLabel("<b>Text Generation</b>"))
        text_key_layout = QHBoxLayout()
        text_key_layout.addWidget(QLabel("OpenAI API Key:"))
        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        text_key_layout.addWidget(self.openai_key)
        self.text_key_validate_btn = QPushButton("Validate Key")
        qconnect(self.text_key_validate_btn.clicked, self.validate_openai_key)
        text_key_layout.addWidget(self.text_key_validate_btn)
        layout.addLayout(text_key_layout)
        layout.addWidget(QLabel("GPT Prompt:"))
        self.gpt_prompt_input = QTextEdit()
        self.gpt_prompt_input.setFixedHeight(80)
        layout.addWidget(self.gpt_prompt_input)

        # =====================
        # TTS Generation
        # =====================
        layout.addWidget(QLabel("<b>TTS Generation</b>"))
        engine_layout = QHBoxLayout()
        engine_layout.addWidget(QLabel("Engine:"))
        self.tts_engine_combo = QComboBox()
        self.tts_engine_combo.addItems(["VoiceVox","ElevenLabs","OpenAI TTS"])
        qconnect(self.tts_engine_combo.currentIndexChanged, self.update_tts_panels)
        engine_layout.addWidget(self.tts_engine_combo)
        layout.addLayout(engine_layout)

        # VoiceVox subpanel
        self.panel_voicevox = QWidget()
        pv = QVBoxLayout(self.panel_voicevox)
        self.voicevox_test_btn = QPushButton("Test VoiceVox Connection")
        qconnect(self.voicevox_test_btn.clicked, self.test_voicevox_connection)
        pv.addWidget(self.voicevox_test_btn)
        layout.addWidget(self.panel_voicevox)

        # ElevenLabs subpanel
        self.panel_elevenlabs = QWidget()
        pel = QVBoxLayout(self.panel_elevenlabs)
        eleven_key_layout = QHBoxLayout()
        eleven_key_layout.addWidget(QLabel("ElevenLabs API Key:"))
        self.elevenlabs_key_input = QLineEdit()
        self.elevenlabs_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        eleven_key_layout.addWidget(self.elevenlabs_key_input)
        self.elevenlabs_validate_btn = QPushButton("Validate Key")
        qconnect(self.elevenlabs_validate_btn.clicked, self.validate_elevenlabs_key)
        eleven_key_layout.addWidget(self.elevenlabs_validate_btn)
        pel.addLayout(eleven_key_layout)
        pel.addWidget(QLabel("Voice:"))
        self.elevenlabs_voice_combo = QComboBox()
        pel.addWidget(self.elevenlabs_voice_combo)
        layout.addWidget(self.panel_elevenlabs)

        # OpenAI TTS subpanel
        self.panel_openai_tts = QWidget()
        poi = QVBoxLayout(self.panel_openai_tts)
        openai_tts_layout = QHBoxLayout()
        openai_tts_layout.addWidget(QLabel("OpenAI TTS Voice:"))
        self.openai_tts_combo = QComboBox()
        self.openai_tts_combo.addItems(["alloy","ash","ballad","coral","echo","fable","nova","onyx","sage","shimmer"])
        openai_tts_layout.addWidget(self.openai_tts_combo)
        self.openai_tts_validate_btn = QPushButton("Validate Key")
        qconnect(self.openai_tts_validate_btn.clicked, self.validate_openai_key)
        openai_tts_layout.addWidget(self.openai_tts_validate_btn)
        poi.addLayout(openai_tts_layout)
        layout.addWidget(self.panel_openai_tts)
        self.update_tts_panels()

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        qconnect(save_button.clicked, self.save_and_close)
        qconnect(cancel_button.clicked, self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

    def update_field_combos(self):
        note_type = self.note_type_combo.currentText()
        fields = get_fields_for_note_type(note_type)
        
        # Clear and update all field comboboxes
        for combo in [self.word_field_combo, self.sentence_field_combo, 
                      self.definition_field_combo,
                      self.explanation_field_combo, self.explanation_audio_field_combo]:
            current_text = combo.currentText()
            combo.clear()
            combo.addItems(fields)
        
        # Verify if selected fields exist in the note type
        self.verify_fields()

    def verify_fields(self):
        """Verify if the selected fields exist in the note type and show warnings if not"""
        note_type = self.note_type_combo.currentText()
        fields = get_fields_for_note_type(note_type)
        
        missing_fields = []
        
        # Check audio field specifically since it's critical for audio generation
        audio_field = self.explanation_audio_field_combo.currentText()
        if audio_field and audio_field not in fields:
            missing_fields.append(f"'{audio_field}' (audio)")
        
        if missing_fields:
            warning = f"Warning: The following fields are not in the note type '{note_type}':<br>"
            warning += "<br>".join(missing_fields)
            warning += "<br><br>You may need to add these fields to your note type or select different fields."
            self.field_verification_label.setText(warning)
        else:
            self.field_verification_label.setText("")

    def load_settings(self):
        load_config()
        
        # Set note type selection: use configured value or default to first available
        note_types = get_note_types()
        if CONFIG["note_type"] in note_types:
            self.note_type_combo.setCurrentText(CONFIG["note_type"])
        else:
            if note_types:
                self.note_type_combo.setCurrentIndex(0)
                CONFIG["note_type"] = note_types[0]
        # Update field combos based on selected note type
        self.update_field_combos()
        
        # Set field values
        field_combos = {
            "word_field": self.word_field_combo,
            "sentence_field": self.sentence_field_combo,
            "definition_field": self.definition_field_combo,
            "explanation_field": self.explanation_field_combo,
            "explanation_audio_field": self.explanation_audio_field_combo
        }
        
        for field_name, combo in field_combos.items():
            if CONFIG[field_name] and CONFIG[field_name] in [combo.itemText(i) for i in range(combo.count())]:
                combo.setCurrentText(CONFIG[field_name])
        
        # Load Text Generation settings
        self.openai_key.setText(CONFIG["openai_key"])
        self.gpt_prompt_input.setPlainText(CONFIG["gpt_prompt"])
        # Load TTS settings
        self.tts_engine_combo.setCurrentText(CONFIG["tts_engine"])
        self.elevenlabs_key_input.setText(CONFIG["elevenlabs_key"])
        # Populate ElevenLabs voice if previously valid
        if CONFIG["elevenlabs_voice_id"]:
            self.elevenlabs_voice_combo.setCurrentText(CONFIG["elevenlabs_voice_id"])
        self.openai_tts_combo.setCurrentText(CONFIG["openai_tts_voice"])
        self.update_tts_panels()

    def save_and_close(self):
        # Update config with dialog values
        CONFIG["note_type"] = self.note_type_combo.currentText()
        CONFIG["word_field"] = self.word_field_combo.currentText()
        CONFIG["sentence_field"] = self.sentence_field_combo.currentText()
        CONFIG["definition_field"] = self.definition_field_combo.currentText()
        CONFIG["explanation_field"] = self.explanation_field_combo.currentText()
        CONFIG["explanation_audio_field"] = self.explanation_audio_field_combo.currentText()
        # Save Text Generation settings
        CONFIG["openai_key"] = self.openai_key.text()
        CONFIG["gpt_prompt"] = self.gpt_prompt_input.toPlainText()
        # Save TTS settings
        CONFIG["tts_engine"] = self.tts_engine_combo.currentText()
        CONFIG["elevenlabs_key"] = self.elevenlabs_key_input.text()
        CONFIG["elevenlabs_voice_id"] = self.elevenlabs_voice_combo.currentText()
        CONFIG["openai_tts_voice"] = self.openai_tts_combo.currentText()
        # Save to disk
        save_config()
        self.accept()

    def update_tts_panels(self):
        # Show the panel matching the selected TTS engine only
        engine = self.tts_engine_combo.currentText()
        self.panel_voicevox.setVisible(engine == "VoiceVox")
        self.panel_elevenlabs.setVisible(engine == "ElevenLabs")
        self.panel_openai_tts.setVisible(engine == "OpenAI TTS")

    def validate_elevenlabs_key(self):
        # Fetch the voices list from ElevenLabs
        key = self.elevenlabs_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Missing Key", "Please enter your ElevenLabs API key.")
            return
        try:
            r = requests.get("https://api.elevenlabs.io/v2/voices", headers={"xi-api-key": key}, timeout=10)
            r.raise_for_status()
            data = r.json().get("voices", [])
            self.elevenlabs_voice_combo.clear()
            for v in data:
                name = v.get("name") or v.get("voice_id")
                vid = v.get("voice_id")
                self.elevenlabs_voice_combo.addItem(name, vid)
            QMessageBox.information(self, "Voices Loaded", f"Loaded {len(data)} voices.")
        except Exception as e:
            QMessageBox.critical(self, "Validation Failed", f"Could not load voices: {e}")

    def validate_openai_key(self):
        # Simple check for OpenAI key validity
        key = self.openai_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Missing Key", "Please enter your OpenAI API key.")
            return
        try:
            h = {"Authorization": f"Bearer {key}"}
            r = requests.get("https://api.openai.com/v1/models", headers=h, timeout=10)
            r.raise_for_status()
            QMessageBox.information(self, "Key Valid", "OpenAI API key is valid.")
        except Exception as e:
            QMessageBox.critical(self, "Validation Failed", f"Key validation failed: {e}")

    def test_voicevox_connection(self):
        """Test the connection to VOICEVOX and show detailed results"""
        try:
            # Try to connect to VOICEVOX with more detailed diagnostics
            is_running = check_voicevox_running()
            
            if is_running:
                # Try to generate a very small test audio to confirm full functionality
                test_text = "テスト"
                test_result = generate_audio("", test_text)
                
                if test_result:
                    # Success! Show confirmation message with path to audio file
                    QMessageBox.information(self, "VOICEVOX Connection Successful", 
                        f"Successfully connected to VOICEVOX and generated test audio.\n\n"
                        f"Audio file: {test_result}\n\n"
                        f"Audio generation should work correctly.")
                else:
                    # Connected but couldn't generate audio
                    QMessageBox.warning(self, "VOICEVOX Partial Connection", 
                        "Connected to VOICEVOX server, but failed to generate test audio.\n\n"
                        "Possible issues:\n"
                        "- VOICEVOX server is running but not responding to synthesis requests\n"
                        "- Permission issues with the media directory\n"
                        "- Audio generation timeout\n\n"
                        "Please check the debug logs for more details.")
            else:
                # Couldn't connect to VOICEVOX
                QMessageBox.critical(self, "VOICEVOX Connection Failed", 
                    "Failed to connect to VOICEVOX server.\n\n"
                    "Please ensure VOICEVOX is running and the API server is enabled.\n\n"
                    "Common issues:\n"
                    "- VOICEVOX application is not started\n"
                    "- API server is disabled in VOICEVOX settings\n"
                    "- VOICEVOX is using a different port (default is 50021)\n"
                    "- Firewall is blocking connections to VOICEVOX\n\n" +
                    get_voicevox_install_instructions())
        except Exception as e:
            # Error during test
            QMessageBox.critical(self, "Test Error", 
                f"An error occurred while testing VOICEVOX connection:\n\n{str(e)}")

# Process a single note with debug mode
def process_note_debug(note, override_text, override_audio, progress_callback=None):
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    debug_log_path = os.path.join(addon_dir, "process_debug.txt")
    
    def debug_write(message):
        try:
            with open(debug_log_path, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(message)
        except Exception as e:
            print(f"Failed to write to debug log: {e}")
    
    debug_write("=== PROCESS NOTE START ===")
    debug_write(f"Note ID: {note.id}")
    
    try:
        if not CONFIG["openai_key"]:
            debug_write("No API key set")
            return False, "No OpenAI API key set. Please set your API key in the settings."

        # Extract data from note
        debug_write("Extracting data from note")
        word = note[CONFIG["word_field"]] if CONFIG["word_field"] in note else ""
        sentence = note[CONFIG["sentence_field"]] if CONFIG["sentence_field"] in note else ""
        definition = note[CONFIG["definition_field"]] if CONFIG["definition_field"] in note else ""
        debug_write(f"Word field: {CONFIG['word_field']} = {word[:30]}...")
        debug_write(f"Sentence field: {CONFIG['sentence_field']} = {sentence[:30]}...")
        debug_write(f"Definition field: {CONFIG['definition_field']} = {definition[:30]}...")
        
        # Skip only if neither text nor audio override is requested and both contents exist
        if not override_text and not override_audio:
            debug_write("Checking if content already exists")
            explanation_exists = CONFIG["explanation_field"] in note and note[CONFIG["explanation_field"]].strip()
            # Check if audio field exists in the note before checking its content
            audio_exists = CONFIG["explanation_audio_field"] in note and note[CONFIG["explanation_audio_field"]].strip()
            
            debug_write(f"explanation exists: {explanation_exists}")
            debug_write(f"Audio exists: {audio_exists}")
            
            # Skip if both fields already have content
            if explanation_exists and audio_exists:
                debug_write("Both fields have content, skipping")
                return True, "Content already exists"
        
        # Process with OpenAI
        debug_write("Preparing prompt for OpenAI")
        prompt = CONFIG["gpt_prompt"].format(
            word=word,
            sentence=sentence,
            definition=definition
        )
        
        debug_write("Calling process_with_openai")
        try:
            if progress_callback:
                progress_callback("Sending request to OpenAI...")
                
            explanation = process_with_openai(CONFIG["openai_key"], prompt)
            if not explanation:
                debug_write("Failed to generate explanation from OpenAI")
                log_error("Failed to generate explanation from OpenAI")
                return False, "Failed to generate explanation from OpenAI"
            debug_write(f"Received explanation: {explanation[:50]}...")
            
            if progress_callback:
                progress_callback("Received explanation from OpenAI")
        except Exception as e:
            debug_write(f"Error in process_with_openai: {str(e)}")
            log_error("Error in process_with_openai", e)
            return False, f"Error calling OpenAI API: {str(e)}"
        
        # Save explanation to note
        if CONFIG["explanation_field"] in note:
            debug_write(f"Saving explanation to field: {CONFIG['explanation_field']}")
            if override_text or not note[CONFIG["explanation_field"]].strip():
                try:
                    note[CONFIG["explanation_field"]] = explanation
                    debug_write("explanation saved to note")
                    
                    if progress_callback:
                        progress_callback("explanation saved to note")
                except Exception as e:
                    debug_write(f"Error setting explanation field: {str(e)}")
                    log_error(f"Error setting explanation field: {CONFIG['explanation_field']}", e)
                    return False, f"Error saving explanation to note: {str(e)}"
        
        # Also try the "explanation" field (with correct spelling) if it exists
        if "explanation" in note and CONFIG["explanation_field"] != "explanation":
            debug_write("Also saving to 'explanation' field (correct spelling)")
            if override_text or not note["explanation"].strip():
                try:
                    note["explanation"] = explanation
                    debug_write("Explanation saved to note (correct spelling field)")
                except Exception as e:
                    debug_write(f"Error setting explanation field (correct spelling): {str(e)}")
                    # Continue even if this fails
        
        # Audio generation using the selected TTS engine
        debug_write("Starting audio generation step")
        audio_path_result = [None]
        # Only generate if the audio field exists and override_audio is True or the field is empty
        if CONFIG["explanation_audio_field"] in note:
            debug_write(f"Audio field found: {CONFIG['explanation_audio_field']}")
            if override_audio or not note[CONFIG["explanation_audio_field"]].strip():
                try:
                    debug_write(f"Calling generate_audio with engine: {CONFIG['tts_engine']}")
                    audio_path = generate_audio(CONFIG.get("openai_key", ""), explanation)
                    if audio_path:
                        debug_write(f"Audio generated: {audio_path}")
                        audio_path_result[0] = audio_path
                except Exception as e:
                    debug_write(f"Error during audio generation: {str(e)}")
                # Save result or placeholder
                if audio_path_result[0]:
                    audio_filename = os.path.basename(audio_path_result[0])
                    note[CONFIG["explanation_audio_field"]] = f"[sound:{audio_filename}]"
                    debug_write("Audio reference saved to note")
                else:
                    note[CONFIG["explanation_audio_field"]] = "[Audio generation skipped or failed]"
                    debug_write("Audio generation skipped or failed, placeholder saved")
        else:
            debug_write(f"Audio field not found in note: {CONFIG['explanation_audio_field']}")
        
        # Also try the "explanationAudio" field (with correct spelling) if it exists
        if "explanationAudio" in note and CONFIG["explanation_audio_field"] != "explanationAudio":
            debug_write("Checking for 'explanationAudio' field (correct spelling)")
            if audio_path_result[0]:
                audio_filename = os.path.basename(audio_path_result[0])
                note["explanationAudio"] = f"[sound:{audio_filename}]"
                debug_write("Audio reference saved to explanationAudio field (correct spelling)")
            else:
                note["explanationAudio"] = "[Audio generation skipped or failed]"
                debug_write("Audio generation was skipped or failed, setting placeholder text")
        
        # Save changes - wrap in try/except to catch any issues
        try:
            debug_write("Calling note.flush() to save changes")
            
            if progress_callback:
                progress_callback("Saving changes to note...")
                
            note.flush()
            debug_write("Note.flush() completed successfully")
            
            if progress_callback:
                progress_callback("Changes saved successfully")
        except Exception as e:
            debug_write(f"Error in note.flush(): {str(e)}")
            log_error("Error in note.flush()", e)
            return False, f"Error saving changes to note: {str(e)}"
            
        debug_write("=== PROCESS NOTE COMPLETED SUCCESSFULLY ===")
        return True, "Process completed successfully"
    except Exception as e:
        debug_write(f"Unexpected error in process_note: {str(e)}")
        debug_write(f"Stack trace: {traceback.format_exc()}")
        log_error("Unexpected error in process_note", e)
        return False, f"Unexpected error: {str(e)}"

# Replace the original process_note function with the debug version
process_note = process_note_debug

# Process the current card during review
def process_current_card():
    try:
        if mw.state != "review" or not mw.reviewer.card:
            tooltip("No card is being reviewed.")
            return
        
        card = mw.reviewer.card
        note = card.note()
        
        # Create a progress dialog with a visible progress bar
        progress = QProgressDialog("Initializing...", "Cancel", 0, 100, mw)
        progress.setWindowTitle("GPT LanguageExplainer")
        progress.setMinimumDuration(0)  # Show immediately
        progress.setAutoClose(False)    # Don't close automatically
        progress.setAutoReset(False)    # Don't reset automatically
        
        # Fix for Qt6 compatibility - use Qt.WindowModality.ApplicationModal instead of Qt.WindowModal
        try:
            # Try Qt6 style enum first
            progress.setWindowModality(Qt.WindowModality.ApplicationModal) 
        except AttributeError:
            # Fallback to Qt5 style for backwards compatibility
            try:
                progress.setWindowModality(Qt.ApplicationModal)
            except:
                # Last resort fallback - don't set modality if both approaches fail
                log_error("Failed to set window modality - Qt version compatibility issue")
                
        progress.setMinimumWidth(400)   # Set a fixed minimum width to prevent resizing issues
        progress.setValue(0)
        progress.setLabelText("Checking note type...")
        progress.show()  # Explicitly show the dialog
        
        # Process UI events to ensure dialog is displayed
        QApplication.processEvents()
        
        # Check note type (updated for Anki 25+)
        model_name = note.note_type()["name"]
        if model_name != CONFIG["note_type"]:
            progress.cancel()
            tooltip(f"Current card is not a {CONFIG['note_type']} note.")
            return
        
        progress.setValue(20)
        progress.setLabelText("Checking existing content...")
        QApplication.processEvents()
        
        # Check if explanation already exists
        explanation_exists = CONFIG["explanation_field"] in note and note[CONFIG["explanation_field"]].strip()
        audio_exists = CONFIG["explanation_audio_field"] in note and note[CONFIG["explanation_audio_field"]].strip()
        
        # Ask separate override questions
        override_text = askUser("Do you want to override the text?", title="GPT Explainer", defaultno=False)
        override_audio = askUser("Do you want to override the voice field?", title="GPT Explainer", defaultno=False)
        # Store audio override flag to skip audio generation in backend
        CONFIG["override_audio"] = override_audio
        # Proceed directly to voicevox status check
        progress.setValue(30)
        progress.setLabelText("Checking VOICEVOX status...")
        QApplication.processEvents()
        
        progress.setValue(40)
        progress.setLabelText("Generating explanation with OpenAI...")
        QApplication.processEvents()
        
        # Set up a watchdog timer to detect if processing gets stuck
        processing_timeout = 60  # seconds
        processing_start_time = time.time()
        processing_completed = [False]  # Use a list to allow modification in nested functions
        timer = [None]  # Store the timer in a list to access it from nested functions
        
        # Create a timer to check if processing is taking too long
        def check_timeout():
            if not processing_completed[0]:
                elapsed_time = time.time() - processing_start_time
                if elapsed_time > processing_timeout:
                    log_error(f"Processing timeout after {elapsed_time:.1f} seconds")
                    mw.taskman.run_on_main(lambda: handle_timeout())
                    # Stop the timer
                    if timer[0]:
                        timer[0].stop()
            else:
                # Stop the timer once processing is completed
                if timer[0]:
                    timer[0].stop()
        
        def handle_timeout():
            try:
                if not processing_completed[0] and progress and not progress.wasCanceled():
                    progress.cancel()
                    error_dialog = QMessageBox(mw)
                    error_dialog.setIcon(QMessageBox.Icon.Warning)
                    error_dialog.setWindowTitle("Processing Timeout")
                    error_dialog.setText("The operation is taking longer than expected.")
                    error_dialog.setInformativeText("The process might be stuck. Check the error logs for details.")
                    error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
                    error_dialog.exec()
            except Exception as e:
                log_error(f"Error in handle_timeout: {str(e)}")
        
        # Start the timeout checker using QTimer
        timer[0] = QTimer(mw)
        timer[0].timeout.connect(check_timeout)
        timer[0].start(5000)  # Check every 5 seconds
        
        # Process the note in a separate thread to keep UI responsive
        def process_with_progress():
            try:
                # Create a callback function to update the progress dialog
                def update_progress(message):
                    # Update progress value based on the stage of processing
                    progress_value = 40
                    if "Sending request to OpenAI" in message:
                        progress_value = 50
                    elif "Received explanation from OpenAI" in message:
                        progress_value = 70
                        log_error(f"Progress update: {message}, value: {progress_value}")
                    elif "explanation saved to note" in message:
                        progress_value = 75
                        log_error(f"Progress update: {message}, value: {progress_value}")
                    elif "Generating audio" in message:
                        progress_value = 80
                        log_error(f"Progress update: {message}, value: {progress_value}")
                    elif "Audio generated" in message:
                        progress_value = 90
                        log_error(f"Progress update: {message}, value: {progress_value}")
                    elif "Audio generation failed" in message or "Error generating audio" in message:
                        progress_value = 85
                        log_error(f"Progress update: {message}, value: {progress_value}")
                    elif "VOICEVOX not running" in message:
                        progress_value = 85
                        log_error(f"Progress update: {message}, value: {progress_value}")
                    elif "Saving changes" in message:
                        progress_value = 95
                        log_error(f"Progress update: {message}, value: {progress_value}")
                    elif "Changes saved successfully" in message:
                        progress_value = 98
                        log_error(f"Progress update: {message}, value: {progress_value}")
                    
                    # Force UI update on main thread
                    mw.taskman.run_on_main(lambda: update_progress_ui(message, progress_value))
                
                def update_progress_ui(message, value):
                    try:
                        if progress.wasCanceled():
                            log_error("Progress dialog was canceled, skipping update")
                            return
                            
                        progress.setValue(value)
                        progress.setLabelText(message)
                        QApplication.processEvents()
                        log_error(f"UI updated: {message}, value: {value}")
                    except Exception as e:
                        log_error(f"Error updating progress UI: {str(e)}")
                
                # Call process_note with the progress callback
                log_error("Starting process_note with progress callback")
                result, message = process_note(note, override_text, override_audio, update_progress)
                log_error(f"process_note completed with result: {result}, message: {message}")
                
                # Mark processing as completed to stop the timeout checker
                processing_completed[0] = True
                
                # Update UI on the main thread
                mw.taskman.run_on_main(lambda: handle_process_result(result, message, card, progress))
            except Exception as e:
                # Mark processing as completed to stop the timeout checker
                processing_completed[0] = True
                
                error_msg = str(e)
                log_error("Error in process_with_progress", e)
                mw.taskman.run_on_main(lambda: show_error(error_msg, progress))
        
        # Function to handle the result on the main thread
        def handle_process_result(success, message, card, progress):
            try:
                if success:
                    progress.setValue(100)
                    progress.setLabelText("Refreshing card...")
                    QApplication.processEvents()
                    try:
                        card.load()  # Refresh the card to show new content
                        progress.cancel()
                        tooltip("explanation generated successfully!")
                    except Exception as e:
                        log_error("Error in card.load()", e)
                        progress.cancel()
                        tooltip("explanation generated, but failed to refresh card.")
                else:
                    progress.cancel()
                    error_dialog = QMessageBox(mw)
                    error_dialog.setIcon(QMessageBox.Icon.Critical)
                    error_dialog.setWindowTitle("Error")
                    error_dialog.setText("Failed to generate explanation")
                    error_dialog.setInformativeText(message)
                    error_dialog.setDetailedText(f"Please check the error log for more details.\n\nError: {message}")
                    error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
                    error_dialog.exec()
            except Exception as e:
                log_error(f"Error in handle_process_result: {str(e)}")
                try:
                    progress.cancel()
                except:
                    pass
                tooltip("An error occurred while handling the result.")
        
        # Function to show error on the main thread
        def show_error(error_msg, progress):
            try:
                progress.cancel()
                error_dialog = QMessageBox(mw)
                error_dialog.setIcon(QMessageBox.Icon.Critical)
                error_dialog.setWindowTitle("Error")
                error_dialog.setText("Failed to generate explanation")
                error_dialog.setInformativeText(f"Error: {error_msg}")
                error_dialog.setDetailedText(f"Please check the error log for more details.\n\nError: {error_msg}")
                error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
                error_dialog.exec()
            except Exception as e:
                log_error(f"Error in show_error: {str(e)}")
                tooltip(f"Error: {error_msg}")
        
        # Start processing in a separate thread
        threading.Thread(target=process_with_progress).start()
        
    except Exception as e:
        log_error("Unexpected error in process_current_card", e)
        tooltip("An error occurred. Check the error log for details.")

# Add the button to the card during review
def add_button_to_reviewer():
    try:
        log_error("Adding button to reviewer")
        
        # Get reviewer bottombar element
        bottombar = mw.reviewer.bottom.web
        
        # Create JavaScript code to add button
        js = """
        (function() {
            console.log('Running GPT button script');
            
            // Check if the button already exists
            if (document.getElementById('gpt-button')) {
                console.log('Button already exists, skipping');
                return;
            }
            
            // Create the button
            var button = document.createElement('button');
            button.id = 'gpt-button';
            button.className = 'btn';
            button.style.margin = '5px';
            button.style.padding = '6px 12px';
            button.style.fontSize = '14px';
            button.style.cursor = 'pointer';
            button.style.backgroundColor = '#4CAF50';
            button.style.color = 'white';
            button.style.border = 'none';
            button.style.borderRadius = '4px';
            button.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
            
            button.innerText = 'Generate explanation';
            
            // Set up the click handler with debugging
            button.onclick = function() {
                console.log('Generate explanation button clicked');
                pycmd('gpt_explanation');
                return false;
            };
            
            // Create a fixed position container at the top of the screen
            var buttonContainer = document.createElement('div');
            buttonContainer.id = 'gpt-button-container';
            buttonContainer.style.position = 'fixed';
            buttonContainer.style.top = '10px';
            buttonContainer.style.left = '25%';
            buttonContainer.style.transform = 'translateX(-50%)';
            buttonContainer.style.zIndex = '9999';
            buttonContainer.style.textAlign = 'center';
            buttonContainer.style.backgroundColor = 'rgba(240, 240, 240, 0.9)';
            buttonContainer.style.padding = '5px 10px';
            buttonContainer.style.borderRadius = '5px';
            buttonContainer.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)';
            
            buttonContainer.appendChild(button);
            
            // Add to the document body
            document.body.appendChild(buttonContainer);
            
            console.log('GPT Language Explainer button added successfully');
        })();
        """
        
        # Inject JavaScript code
        bottombar.eval(js)
        log_error("JavaScript injected to add button")
    except Exception as e:
        log_error(f"Error adding button to reviewer: {str(e)}")
        log_error(traceback.format_exc())

# Set up the hook to add the button when a card is shown
def on_card_shown(card=None):
    try:
        # Log for debugging
        log_error(f"on_card_shown called with card: {card}")
        
        # Only add the button when the answer is shown
        if mw.state != "review":
            log_error("Not in review state, skipping button addition")
            return
            
        if not mw.reviewer.card:
            log_error("No card in reviewer, skipping button addition")
            return
            
        if not mw.reviewer.state == "answer":
            log_error("Not showing answer, skipping button addition")
            return
        
        # Use the card parameter if provided, otherwise fall back to mw.reviewer.card
        current_card = card if card else mw.reviewer.card
        log_error(f"Current card ID: {current_card.id}")
        
        # Get the note type
        note_type_name = current_card.note().note_type()["name"]
        log_error(f"Note type: {note_type_name}, Config note type: {CONFIG['note_type']}")
        
        if note_type_name == CONFIG["note_type"]:
            log_error("Note type matches, adding button")
            add_button_to_reviewer()
        else:
            log_error(f"Note type doesn't match, skipping button addition")
    except Exception as e:
        log_error(f"Error in on_card_shown: {str(e)}")
        log_error(traceback.format_exc())

# Handle reviewer commands
def on_js_message(handled, message, context):
    # Log the message for debugging
    log_error(f"Received message: {message}, handled: {handled}, context: {context}")
    
    # In Anki 25, the message might be a tuple or a string
    cmd = None
    if isinstance(message, tuple):
        cmd = message[0]
        log_error(f"Message is tuple, cmd: {cmd}")
    else:
        cmd = message
        log_error(f"Message is string, cmd: {cmd}")
    
    # Check if this is our command
    if cmd == "gpt_explanation":
        log_error("Recognized gpt_explanation command, processing...")
        process_current_card()
        
        # Try to detect Anki version to return appropriate value
        try:
            import anki
            anki_version = int(anki.buildinfo.version.split('.')[0])
            log_error(f"Anki version: {anki_version}")
            if anki_version >= 25:
                log_error("Returning (True, None) for Anki 25+")
                return (True, None)
            else:
                log_error("Returning True for older Anki")
                return True
        except Exception as e:
            log_error(f"Error detecting Anki version: {e}")
            # If we can't determine version, return a tuple which works in Anki 25
            return (True, None)
    
    log_error(f"Not our command, returning handled: {handled}")
    return handled

# Set up menu items
def setup_menu():
    # Add the menu option to open settings
    action = QAction("GPT Language Explainer Settings", mw)
    qconnect(action.triggered, open_settings)
    mw.form.menuTools.addAction(action)
    
    # Enable browser menu action for bulk processing
    log_error("Registering browser_menus_did_init hook for batch processing")
    gui_hooks.browser_menus_did_init.append(setup_browser_menu)
    log_error("Browser hook registered")

# Open settings dialog
def open_settings():
    dialog = ConfigDialog(mw)
    dialog.exec()

# Batch process selected notes from the browser
def batch_process_notes():
    from aqt.qt import QProgressDialog, QMessageBox
    
    browser = mw.app.activeWindow()
    if not isinstance(browser, Browser):
        showInfo("Please open this from the Browser view")
        return
    
    # Get selected note ids
    selected_notes = browser.selectedNotes()
    if not selected_notes:
        showInfo("No cards selected. Please select cards to process.")
        return
    
    # Check if configuration is loaded
    if not CONFIG["openai_key"]:
        showInfo("Please set your OpenAI API key in the GPT Language Explainer Settings.")
        return
    
    # Ask if user wants to overwrite text only
    override_text = askUser("Do you want to override the text?", title="GPT Explainer", defaultno=False)
    # Ask if user wants to overwrite the voice field
    override_audio = askUser("Do you want to override the voice field?", title="GPT Explainer", defaultno=False)
    # Store audio override flag to skip audio generation in backend
    CONFIG["override_audio"] = override_audio
    
    # Create a progress dialog with fixed width to avoid the resizing issue
    progress = QProgressDialog("Processing cards...", "Cancel", 0, len(selected_notes) + 1, mw)
    progress.setWindowTitle("GPT Language Explainer Batch Processing")
    
    # Fix for Qt6 compatibility - use Qt.WindowModality.ApplicationModal instead of Qt.WindowModal
    try:
        # Try Qt6 style enum first
        progress.setWindowModality(Qt.WindowModality.ApplicationModal) 
    except AttributeError:
        # Fallback to Qt5 style for backwards compatibility
        try:
            progress.setWindowModality(Qt.ApplicationModal)
        except:
            # Last resort fallback - don't set modality if both approaches fail
            log_error("Failed to set window modality - Qt version compatibility issue")
            
    progress.setMinimumWidth(400)  # Set fixed width to avoid resizing issue
    progress.setValue(0)
    progress.show()
    
    # Process notes in a separate thread to keep UI responsive
    def process_notes_thread():
        success_count = 0
        skipped_count = 0
        error_count = 0
        missing_fields_count = 0
        
        try:
            for i, note_id in enumerate(selected_notes):
                if progress.wasCanceled():
                    break
                
                note = mw.col.get_note(note_id)
                
                # Update progress UI from main thread
                mw.taskman.run_on_main(lambda i=i, total=len(selected_notes): 
                    progress.setLabelText(f"Processing card {i+1} of {total}..."))
                mw.taskman.run_on_main(lambda i=i: progress.setValue(i+1))
                
                # Skip processing if note type doesn't match configured type
                model_name = note.note_type()["name"]
                if model_name != CONFIG["note_type"]:
                    log_error(f"Skipping note {note_id}: Note type {model_name} doesn't match configured type {CONFIG['note_type']}")
                    missing_fields_count += 1
                    continue
                
                # Skip processing if required fields are missing
                required_fields = [CONFIG["word_field"], CONFIG["sentence_field"], CONFIG["definition_field"]]
                if not all(field in note and field in note.keys() for field in required_fields):
                    log_error(f"Skipping note {note_id}: Missing required fields")
                    missing_fields_count += 1
                    continue
                
                # Process the note with separate override flags
                success, message = process_note_debug(note, override_text, override_audio)
                if success:
                    if message == "Content already exists":
                        skipped_count += 1
                    else:
                        success_count += 1
                        # Save changes to the database
                        note.flush()
                else:
                    error_count += 1
            
            # Final update on main thread
            mw.taskman.run_on_main(lambda: progress.setValue(len(selected_notes) + 1))
            
            # Show results
            mw.taskman.run_on_main(lambda: 
                showInfo(f"Batch processing complete:\n"
                         f"{success_count} cards processed successfully\n"
                         f"{skipped_count} cards skipped (already had content)\n"
                         f"{missing_fields_count} cards skipped (missing fields or wrong note type)\n"
                         f"{error_count} cards failed"))
            
        except Exception as e:
            log_error(f"Error in batch processing: {str(e)}")
            log_error(traceback.format_exc())
            mw.taskman.run_on_main(lambda: 
                showInfo(f"Error in batch processing: {str(e)}"))
        finally:
            mw.taskman.run_on_main(lambda: progress.hide())
    
    # Start processing thread
    threading.Thread(target=process_notes_thread, daemon=True).start()

# Add browser menu action for bulk processing
def setup_browser_menu(browser):
    log_error("Setting up browser menu for batch processing")
    
    # Test if we can access the menu
    if hasattr(browser.form, 'menuEdit'):
        log_error("Browser has menuEdit attribute")
    else:
        log_error("Browser does NOT have menuEdit attribute - trying alternative approach")
        # Backwards compatibility with different Anki versions
        try:
            # Try to find the Edit menu by name
            for menu in browser.form.menubar.findChildren(QMenu):
                if menu.title() == "Edit":
                    log_error("Found Edit menu by title")
                    action = QAction("Batch Generate GPT Explanations", browser)
                    qconnect(action.triggered, batch_process_notes)
                    menu.addSeparator()
                    menu.addAction(action)
                    log_error("Action added to Edit menu found by title")
                    return
        except Exception as e:
            log_error(f"Error finding Edit menu: {str(e)}")
    
    # Original implementation
    try:
        action = QAction("Batch Generate GPT Explanations", browser)
        qconnect(action.triggered, batch_process_notes)
        browser.form.menuEdit.addSeparator()
        browser.form.menuEdit.addAction(action)
        log_error("Browser menu setup complete")
    except Exception as e:
        log_error(f"Error setting up browser menu: {str(e)}")
        
        # Try adding to a different menu as fallback
        try:
            log_error("Trying to add to Tools menu instead")
            action = QAction("Batch Generate GPT Explanations", browser)
            qconnect(action.triggered, batch_process_notes)
            browser.form.menuTools.addSeparator()
            browser.form.menuTools.addAction(action)
            log_error("Added action to Tools menu as fallback")
        except Exception as e2:
            log_error(f"Error adding to Tools menu: {str(e2)}")

# Initialize the add-on
def init():
    try:
        log_error("Initializing GPT Language Explainer addon")
        
        # Load configuration
        load_config()
        log_error(f"Configuration loaded: {CONFIG}")
        
        # Set up menu
        setup_menu()
        log_error("Menu setup complete")
        
        # Register hooks
        log_error("Registering hooks")
        
        # Only need to hook into the answer shown event
        gui_hooks.reviewer_did_show_answer.append(on_card_shown)
        log_error("Registered reviewer_did_show_answer hook")
        
        # Register the message handler
        gui_hooks.webview_did_receive_js_message.append(on_js_message)
        log_error("Registered webview_did_receive_js_message hook")
        
        log_error("GPT Language Explainer addon initialization complete")
    except Exception as e:
        log_error(f"Error during initialization: {str(e)}")
        log_error(traceback.format_exc())

# Run initialization
init()