# File: __init__.py
from aqt import mw, gui_hooks
from aqt.utils import qconnect, showInfo, tooltip, askUser
from aqt.qt import QAction, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QLineEdit, QTextEdit, QProgressDialog, QCheckBox, QMessageBox, QApplication, Qt, QTimer, QMenu, QWidget, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QSlider
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
import webbrowser
from aqt.browser import Browser
import requests

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
        tooltip("Installing required dependencies for AI Language Explainer addon...")
        
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
from .api_handler import process_with_openai, generate_audio as backend_generate_audio, check_voicevox_running, check_aivisspeech_running, get_aivisspeech_voices

# Global variables to store configuration
CONFIG = {
    # === Note Configuration ===
    # Which note type and fields to use for processing
    "note_type": "",
    "word_field": "",
    "sentence_field": "",
    "definition_field": "",
    "explanation_field": "",
    "explanation_audio_field": "",
    
    # === OpenAI/Text Generation Settings ===
    "openai_key": "",
    "openai_model": "gpt-4.1",
    "gpt_prompt": "Please write a short explanation of the word '{word}' in the context of the original sentence: '{sentence}'. The definition of the word is: '{definition}'. Write an explanation that helps a Japanese beginner understand the word and how it is used with this context as an example. Explain it in the same way a native would explain it to a child. Don't use any English, only use simpler Japanese. Don't write the furigana for any of the words in brackets after the word. Don't start with stuff like \u3068\u3044\u3046\u8a00\u8449\u3092\u7c21\u5358\u306b\u8aac\u660e\u3059\u308b\u306d, just dive straight into explaining after starting with the word.",
    
    # === TTS/Audio Generation Settings ===
    "tts_engine": "OpenAI TTS",
    # ElevenLabs settings
    "elevenlabs_key": "",
    "elevenlabs_voice_id": "",
    # OpenAI TTS settings
    "openai_tts_voice": "alloy",
    "openai_tts_speed": 1.0,
    # Local TTS engine settings
    "aivisspeech_style_id": None,
    "voicevox_style_id": None,
    
    # === Feature Toggles & UI Preferences ===
    "disable_text_generation": False,
    "disable_audio": False,      
    "hide_button": False
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
    debug_log(f"Final merged config: {CONFIG}")

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

# Bulk Generation Dialog
class BulkGenerationDialog(QDialog):
    """
    Dialog for selecting generation options.
    
    The dialog allows you to select which content to generate for all selected cards.
    - "Generate Text" and "Generate Audio" checkboxes control which content will be generated.
    - When checked, all selected cards will be overridden for that content type.
    - If you do not want a card to be overridden, deselect it in the browser before proceeding.
    Statistics update dynamically to show what will happen with current selections.
    """
    def __init__(self, parent=None, selected_notes=None):
        super(BulkGenerationDialog, self).__init__(parent)
        self.setWindowTitle("AI Language Explainer - Generation Options")
        self.setMinimumWidth(500)
        self.selected_notes = selected_notes or []
        self.setup_ui()
        
        # Initialize result variables  
        self.generate_explanation_text = False
        self.generate_explanation_audio = False
        
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Main instruction label
        instruction_label = QLabel("Select what content to generate:")
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(instruction_label)

        # Explanation text with light color for better visibility
        explanation_text = QLabel(
            "When generation is checked, <b>all</b> selected cards will be overridden for that content type.<br>"
            "Deselect any cards in the browser you do not want to be changed."
        )
        explanation_text.setStyleSheet("""
            QLabel {
                color: #CCCCCC;
                font-size: 13px;
                margin-bottom: 10px;
            }
        """)
        explanation_text.setWordWrap(True)
        layout.addWidget(explanation_text)

        # Primary generation checkboxes (always visible, checked by default)
        self.generate_text_checkbox = QCheckBox("Generate Explanation Text")
        self.generate_audio_checkbox = QCheckBox("Generate Explanation Audio")

        layout.addWidget(self.generate_text_checkbox)
        layout.addWidget(self.generate_audio_checkbox)

        # Connect checkboxes to update statistics
        qconnect(self.generate_text_checkbox.toggled, self.update_statistics)
        qconnect(self.generate_audio_checkbox.toggled, self.update_statistics)

        # Add statistics section with dark mode support
        self.statistics_label = QLabel("")
        self.statistics_label.setStyleSheet("""
            QLabel {
                background-color: palette(alternatebase);
                color: palette(text);
                padding: 10px;
                border-radius: 5px;
                margin-top: 10px;
                border: 1px solid palette(mid);
            }
        """)
        self.statistics_label.setWordWrap(True)
        layout.addWidget(self.statistics_label)

        # Add note about disabled features
        self.note_label = QLabel("")
        self.note_label.setStyleSheet("color: palette(mid); font-style: italic; margin-top: 10px;")
        self.note_label.setWordWrap(True)
        layout.addWidget(self.note_label)

        # Update UI based on current settings
        self.update_checkbox_states()
        self.update_statistics()

        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")

        qconnect(self.ok_button.clicked, self.accept)
        qconnect(self.cancel_button.clicked, self.reject)

        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
    
    def update_checkbox_states(self):
        """Update checkbox states based on current settings and set defaults"""
        text_generation_disabled = CONFIG.get("disable_text_generation", False)
        audio_disabled = CONFIG.get("disable_audio", False)

        # Analyze notes to determine counts for empty fields
        stats = self.analyze_selected_notes() if self.selected_notes else {'empty_text': 0, 'existing_text': 0, 'empty_audio': 0, 'existing_audio': 0}

        notes = []

        # Handle primary text generation checkbox
        if text_generation_disabled:
            self.generate_text_checkbox.setEnabled(False)
            self.generate_text_checkbox.setChecked(False)
            notes.append("Text generation is disabled in settings")
        else:
            self.generate_text_checkbox.setEnabled(True)
            self.generate_text_checkbox.setChecked(True)

        # Handle primary audio generation checkbox  
        if audio_disabled:
            self.generate_audio_checkbox.setEnabled(False)
            self.generate_audio_checkbox.setChecked(False)
            notes.append("Audio generation is disabled in settings")
        else:
            self.generate_audio_checkbox.setEnabled(True)
            self.generate_audio_checkbox.setChecked(True)

        # Show combined notes
        if notes:
            self.note_label.setText("Note: " + ", ".join(notes) + ".")
        else:
            self.note_label.setText("")
    
    def update_statistics(self):
        """Update the statistics display based on current selections and note analysis"""
        if not self.selected_notes:
            self.statistics_label.setText("No notes provided for analysis.")
            return

        # Analyze the selected notes to get statistics
        stats = self.analyze_selected_notes()

        # Determine what will happen based on the checkboxes
        will_generate_text = self.generate_text_checkbox.isChecked() and self.generate_text_checkbox.isEnabled()
        will_generate_audio = self.generate_audio_checkbox.isChecked() and self.generate_audio_checkbox.isEnabled()

        # Format the statistics display
        stats_text = f"<b>Selected Notes Analysis:</b><br>"
        stats_text += f"• {len(self.selected_notes)} total cards selected<br>"
        stats_text += f"• {stats['matching_notes']} cards match configured note type ({CONFIG.get('note_type', 'None')})<br>"

        if stats['matching_notes'] > 0:
            stats_text += f"• {stats['empty_text']} cards have empty explanation text<br>"
            stats_text += f"• {stats['existing_text']} cards have existing explanation text<br>"
            stats_text += f"• {stats['empty_audio']} cards have empty explanation audio<br>"
            stats_text += f"• {stats['existing_audio']} cards have existing explanation audio<br>"

            stats_text += "<br><b>With current settings:</b><br>"
            if will_generate_text:
                stats_text += f"• <b>All</b> selected cards will have explanation text <b>overridden</b><br>"
            if will_generate_audio:
                stats_text += f"• <b>All</b> selected cards will have explanation audio <b>overridden</b><br>"
            if not will_generate_text and not will_generate_audio:
                stats_text += "• <i>No generation will occur with current settings</i>"

        self.statistics_label.setText(stats_text)
    
    def analyze_selected_notes(self):
        """Analyze the selected notes to determine current field states"""
        stats = {
            'matching_notes': 0,
            'empty_text': 0,
            'existing_text': 0,
            'empty_audio': 0,
            'existing_audio': 0
        }
        
        target_note_type = CONFIG.get("note_type", "")
        explanation_field = CONFIG.get("explanation_field", "")
        audio_field = CONFIG.get("explanation_audio_field", "")
        
        for note_id in self.selected_notes:
            try:
                note = mw.col.get_note(note_id)
                
                # Check if note type matches
                if note.note_type()["name"] != target_note_type:
                    continue
                    
                stats['matching_notes'] += 1
                
                # Check explanation text field
                if explanation_field in note:
                    if note[explanation_field].strip():
                        stats['existing_text'] += 1
                    else:
                        stats['empty_text'] += 1
                
                # Check explanation audio field  
                if audio_field in note:
                    if note[audio_field].strip():
                        stats['existing_audio'] += 1
                    else:
                        stats['empty_audio'] += 1
                        
            except Exception as e:
                debug_log(f"Error analyzing note {note_id}: {str(e)}")
                continue
                
        return stats
    
    def get_generation_options(self):
        """Get the selected generation options - returns (generate_text, generate_audio, override_text, override_audio)"""
        generate_text = self.generate_text_checkbox.isChecked() and self.generate_text_checkbox.isEnabled()
        override_text = generate_text  # always override if generate is checked
        generate_audio = self.generate_audio_checkbox.isChecked() and self.generate_audio_checkbox.isEnabled()
        override_audio = generate_audio
        debug_log(f"=== DIALOG GENERATION OPTIONS ===")
        debug_log(f"Generate Text checkbox: {generate_text}, Generate Audio checkbox: {generate_audio}")
        debug_log(f"Override Text: {override_text}, Override Audio: {override_audio}")
        return (generate_text, generate_audio, override_text, override_audio)

# Configuration dialog
class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super(ConfigDialog, self).__init__(parent)
        self.setWindowTitle("AI Language Explainer Settings")
        self.setMinimumWidth(500) # Set a minimum width for the dialog
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # Tab 1: Note & Field Configuration
        note_field_tab = QWidget()
        layout = QVBoxLayout(note_field_tab) # Use 'layout' for this tab's content

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
        layout.addWidget(QLabel("<b>Input Fields</b>")) # Added heading
        word_field_layout = QHBoxLayout()
        word_field_layout.addWidget(QLabel("Word Field: {word}"))
        self.word_field_combo = QComboBox()
        word_field_layout.addWidget(self.word_field_combo)
        layout.addLayout(word_field_layout)
        sentence_field_layout = QHBoxLayout()
        sentence_field_layout.addWidget(QLabel("Sentence Field: {sentence}"))
        self.sentence_field_combo = QComboBox()
        sentence_field_layout.addWidget(self.sentence_field_combo)
        layout.addLayout(sentence_field_layout)
        definition_field_layout = QHBoxLayout()
        definition_field_layout.addWidget(QLabel("Definition Field: {definition}"))
        self.definition_field_combo = QComboBox()
        definition_field_layout.addWidget(self.definition_field_combo)
        layout.addLayout(definition_field_layout)
        
        layout.addWidget(QLabel("<b>Output Fields</b>")) # Added heading
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
        layout.addStretch() # Add stretch to push content to the top
        tab_widget.addTab(note_field_tab, "Note & Fields")

        # Tab 2: UI Preferences
        ui_prefs_tab = QWidget()
        layout = QVBoxLayout(ui_prefs_tab) # Reuse 'layout' for this tab's content

        layout.addWidget(QLabel("<b>UI Preferences</b>"))
        
        # Checkbox for hiding the button
        self.hide_button_checkbox = QCheckBox("Hide 'Generate explanation' button during review")
        layout.addWidget(self.hide_button_checkbox)
        layout.addStretch() # Add stretch
        tab_widget.addTab(ui_prefs_tab, "UI Preferences")
        
        # Tab 3: Text Generation
        text_gen_tab = QWidget()
        layout = QVBoxLayout(text_gen_tab) # Reuse 'layout' for this tab's content

        layout.addWidget(QLabel("<b>Text Generation</b>"))
        
        # Checkbox for disabling text generation
        self.disable_text_generation_checkbox = QCheckBox("Disable text generation")
        layout.addWidget(self.disable_text_generation_checkbox)
        qconnect(self.disable_text_generation_checkbox.toggled, self.update_text_generation_panels)
        
        # Create a container widget for the text generation settings
        self.text_generation_settings_widget = QWidget()
        text_gen_layout = QVBoxLayout(self.text_generation_settings_widget)
        text_gen_layout.setContentsMargins(0, 0, 0, 0)
        
        text_key_layout = QHBoxLayout()
        text_key_layout.addWidget(QLabel("OpenAI API Key:"))
        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        text_key_layout.addWidget(self.openai_key)
        self.text_key_validate_btn = QPushButton("Validate Key")
        qconnect(self.text_key_validate_btn.clicked, self.validate_openai_key)
        text_key_layout.addWidget(self.text_key_validate_btn)
        text_gen_layout.addLayout(text_key_layout)
        
        # Model selection dropdown
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_dropdown = QComboBox()
        self.model_dropdown.addItems([
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano", 
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-3.5-turbo"
        ])
        self.model_dropdown.setCurrentText("gpt-4.1")
        model_layout.addWidget(self.model_dropdown)
        model_layout.addStretch()
        text_gen_layout.addLayout(model_layout)
        
        # Model recommendation text
        model_recommendation = QLabel("gpt-4.1 is recommended as it obeys the prompt well and is reasonably cheap.")
        model_recommendation.setStyleSheet("font-size: 11px; color: #666; font-style: italic; margin-top: 2px;")
        model_recommendation.setWordWrap(True)
        text_gen_layout.addWidget(model_recommendation)
        text_gen_layout.addWidget(QLabel("Prompt:"))
        self.gpt_prompt_input = QTextEdit()
        self.gpt_prompt_input.setFixedHeight(150) # Increased height
        text_gen_layout.addWidget(self.gpt_prompt_input)
        
        layout.addWidget(self.text_generation_settings_widget)
        layout.addStretch() # Add stretch
        tab_widget.addTab(text_gen_tab, "Text Generation")

        # Tab 4: TTS Generation
        tts_gen_tab = QWidget()
        layout = QVBoxLayout(tts_gen_tab) # Reuse 'layout' for this tab's content

        layout.addWidget(QLabel("<b>TTS Generation</b>"))
        
        # Checkbox for disabling audio generation
        self.disable_audio_checkbox = QCheckBox("Disable audio generation")
        layout.addWidget(self.disable_audio_checkbox)
        qconnect(self.disable_audio_checkbox.toggled, self.update_tts_panels)
        
        # Create a container widget for the engine selection
        self.engine_selection_widget = QWidget()
        engine_layout_container = QHBoxLayout(self.engine_selection_widget) # Renamed to avoid conflict
        engine_layout_container.setContentsMargins(0, 0, 0, 0) # Remove extra margins
        engine_layout_container.addWidget(QLabel("Engine:"))
        self.tts_engine_combo = QComboBox()
        self.tts_engine_combo.addItems(["VoiceVox", "ElevenLabs", "OpenAI TTS", "AivisSpeech"])
        qconnect(self.tts_engine_combo.currentIndexChanged, self.update_tts_panels)
        engine_layout_container.addWidget(self.tts_engine_combo)
        layout.addWidget(self.engine_selection_widget) # Add the container widget

        # VoiceVox subpanel
        self.panel_voicevox = QWidget()
        pv = QVBoxLayout(self.panel_voicevox)
        pv.setContentsMargins(0,0,0,0)
        self.voicevox_test_btn = QPushButton("Test VoiceVox Connection")
        qconnect(self.voicevox_test_btn.clicked, self.test_voicevox_connection)
        pv.addWidget(self.voicevox_test_btn)

        # Load Available Voices for VoiceVox
        self.voicevox_load_voices_btn = QPushButton("Load Available Voices")
        qconnect(self.voicevox_load_voices_btn.clicked, self.load_voicevox_voices_ui)
        pv.addWidget(self.voicevox_load_voices_btn)

        # Voices Table for VoiceVox
        self.voicevox_voices_table = QTableWidget()
        self.voicevox_voices_table.setColumnCount(4)
        self.voicevox_voices_table.setHorizontalHeaderLabels(["Speaker", "Style", "Play Sample", "Use as Default"])
        self.voicevox_voices_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.voicevox_voices_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.voicevox_voices_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.voicevox_voices_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.voicevox_voices_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        pv.addWidget(self.voicevox_voices_table)

        layout.addWidget(self.panel_voicevox)

        # ElevenLabs subpanel
        self.panel_elevenlabs = QWidget()
        pel = QVBoxLayout(self.panel_elevenlabs)
        pel.setContentsMargins(0,0,0,0)
        # API Key input and validation
        eleven_key_layout = QHBoxLayout()
        eleven_key_layout.addWidget(QLabel("ElevenLabs API Key:"))
        self.elevenlabs_key_input = QLineEdit()
        self.elevenlabs_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        eleven_key_layout.addWidget(self.elevenlabs_key_input)
        self.elevenlabs_validate_btn = QPushButton("Validate Key")
        qconnect(self.elevenlabs_validate_btn.clicked, self.validate_elevenlabs_key)
        eleven_key_layout.addWidget(self.elevenlabs_validate_btn)
        pel.addLayout(eleven_key_layout)
        # Free-form Voice ID input
        voice_id_layout = QHBoxLayout()
        voice_id_layout.addWidget(QLabel("Voice ID:"))
        self.elevenlabs_voice_id_input = QLineEdit()
        voice_id_layout.addWidget(self.elevenlabs_voice_id_input)
        pel.addLayout(voice_id_layout)
        layout.addWidget(self.panel_elevenlabs)

        # OpenAI TTS subpanel
        self.panel_openai_tts = QWidget()
        poi = QVBoxLayout(self.panel_openai_tts)
        poi.setContentsMargins(0,0,0,0)
        
        # Voice selection row
        openai_tts_layout = QHBoxLayout()
        openai_tts_layout.addWidget(QLabel("OpenAI TTS Voice:"))
        self.openai_tts_combo = QComboBox()
        self.openai_tts_combo.addItems(["alloy","ash","ballad","coral","echo","fable","nova","onyx","sage","shimmer"])
        openai_tts_layout.addWidget(self.openai_tts_combo)
        self.openai_tts_validate_btn = QPushButton("Validate Key")
        qconnect(self.openai_tts_validate_btn.clicked, self.validate_openai_key) # Reconnect OpenAI key validation
        openai_tts_layout.addWidget(self.openai_tts_validate_btn)
        poi.addLayout(openai_tts_layout)
        
        # Speed slider row
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.openai_tts_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.openai_tts_speed_slider.setMinimum(50)  # 0.5 * 100
        self.openai_tts_speed_slider.setMaximum(300) # 3.0 * 100
        self.openai_tts_speed_slider.setValue(100)   # 1.0 * 100 (default)
        self.openai_tts_speed_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.openai_tts_speed_slider.setTickInterval(50)  # Ticks at 0.5, 1.0, 1.5, 2.0, 2.5, 3.0
        speed_layout.addWidget(self.openai_tts_speed_slider)
        
        # Speed value label
        self.openai_tts_speed_label = QLabel("1.0x")
        self.openai_tts_speed_label.setMinimumWidth(40)
        speed_layout.addWidget(self.openai_tts_speed_label)
        
        # Connect slider to update label
        qconnect(self.openai_tts_speed_slider.valueChanged, self.update_speed_label)
        
        poi.addLayout(speed_layout)
        layout.addWidget(self.panel_openai_tts)

        # AivisSpeech subpanel
        self.panel_aivisspeech = QWidget()
        pas = QVBoxLayout(self.panel_aivisspeech)
        pas.setContentsMargins(0,0,0,0)
        
        # Test Connection Button (kept at the top or bottom for consistency)
        self.aivisspeech_test_btn = QPushButton("Test AivisSpeech Connection")
        qconnect(self.aivisspeech_test_btn.clicked, self.test_aivisspeech_connection)
        pas.addWidget(self.aivisspeech_test_btn)

        # Load Voices Button
        self.aivisspeech_load_voices_btn = QPushButton("Load Available Voices")
        qconnect(self.aivisspeech_load_voices_btn.clicked, self.load_aivisspeech_voices_ui)
        pas.addWidget(self.aivisspeech_load_voices_btn)

        # Voices Table
        self.aivisspeech_voices_table = QTableWidget()
        self.aivisspeech_voices_table.setColumnCount(4) # Speaker, Style, Play, Set Default
        self.aivisspeech_voices_table.setHorizontalHeaderLabels(["Speaker", "Style", "Play Sample", "Use as Default"])
        self.aivisspeech_voices_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.aivisspeech_voices_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.aivisspeech_voices_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.aivisspeech_voices_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.aivisspeech_voices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.aivisspeech_voices_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Make table read-only
        pas.addWidget(self.aivisspeech_voices_table)
        
        layout.addWidget(self.panel_aivisspeech)

        self.update_tts_panels() # Call once to set initial visibility
        layout.addStretch() # Add stretch
        tab_widget.addTab(tts_gen_tab, "TTS Generation")

        # Promotional section (appears on all tabs)
        promo_widget = QWidget()
        promo_layout = QVBoxLayout(promo_widget)
        promo_layout.setContentsMargins(10, 8, 10, 5)
        
        # Add minimal spacing
        promo_layout.addWidget(QLabel())  # Empty label for spacing
        
        # Promotional message
        promo_label = QLabel("If you want to learn how to reach native-level fluency as fast as possible, click the button below.")
        promo_label.setWordWrap(True)
        promo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        promo_label.setStyleSheet("font-size: 12px; color: #666; margin: 5px 0px;")
        promo_layout.addWidget(promo_label)
        
        # Promotional button
        promo_button = QPushButton("Learn Language Learning Theory")
        promo_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                margin: 5px 0px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        qconnect(promo_button.clicked, self.open_language_learning_community)
        promo_layout.addWidget(promo_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        main_layout.addWidget(promo_widget)

        # Buttons (common to all tabs, so placed outside the tab_widget)
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        qconnect(save_button.clicked, self.save_and_close)
        qconnect(cancel_button.clicked, self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout) # Add buttons to the main_layout

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
        self.model_dropdown.setCurrentText(CONFIG["openai_model"])
        self.gpt_prompt_input.setPlainText(CONFIG["gpt_prompt"])
        
        # Load TTS settings
        self.tts_engine_combo.setCurrentText(CONFIG["tts_engine"])
        self.elevenlabs_key_input.setText(CONFIG["elevenlabs_key"])
        self.elevenlabs_voice_id_input.setText(CONFIG["elevenlabs_voice_id"])
        self.openai_tts_combo.setCurrentText(CONFIG["openai_tts_voice"])
        
        # Load OpenAI TTS speed setting
        speed_value = CONFIG.get("openai_tts_speed", 1.0)
        self.openai_tts_speed_slider.setValue(int(speed_value * 100))
        self.update_speed_label()  # Update the label to show current value
        
        self.aivisspeech_style_id = CONFIG.get("aivisspeech_style_id")
        self.voicevox_style_id = CONFIG.get("voicevox_style_id")

        # Load UI preference settings
        self.disable_audio_checkbox.setChecked(CONFIG.get("disable_audio", False))
        self.hide_button_checkbox.setChecked(CONFIG.get("hide_button", False))
        self.disable_text_generation_checkbox.setChecked(CONFIG.get("disable_text_generation", False))
        
        self.update_tts_panels()
        self.update_text_generation_panels()

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
        CONFIG["openai_model"] = self.model_dropdown.currentText()
        CONFIG["gpt_prompt"] = self.gpt_prompt_input.toPlainText()

        # Save TTS settings
        CONFIG["tts_engine"] = self.tts_engine_combo.currentText()
        CONFIG["elevenlabs_key"] = self.elevenlabs_key_input.text()
        CONFIG["elevenlabs_voice_id"] = self.elevenlabs_voice_id_input.text()
        CONFIG["openai_tts_voice"] = self.openai_tts_combo.currentText()
        CONFIG["openai_tts_speed"] = self.openai_tts_speed_slider.value() / 100.0

        # Save UI preference settings
        CONFIG["disable_audio"] = self.disable_audio_checkbox.isChecked()
        CONFIG["hide_button"] = self.hide_button_checkbox.isChecked()
        CONFIG["disable_text_generation"] = self.disable_text_generation_checkbox.isChecked()
        
        # Save to disk
        save_config()
        self.accept()

    def update_text_generation_panels(self):
        """Hide/show text generation settings based on disable_text_generation checkbox"""
        # If text generation is disabled, hide all text generation settings
        is_disabled = self.disable_text_generation_checkbox.isChecked()
        self.text_generation_settings_widget.setVisible(not is_disabled)

    def update_speed_label(self):
        """Update the speed label when the slider value changes"""
        speed_value = self.openai_tts_speed_slider.value() / 100.0
        self.openai_tts_speed_label.setText(f"{speed_value:.1f}x")

    def update_tts_panels(self):
        # Show the panel matching the selected TTS engine only
        engine = self.tts_engine_combo.currentText()
        
        # If audio is disabled, hide all TTS panels
        if self.disable_audio_checkbox.isChecked():
            self.panel_voicevox.setVisible(False)
            self.panel_elevenlabs.setVisible(False)
            self.panel_openai_tts.setVisible(False)
            self.panel_aivisspeech.setVisible(False) # Hide AivisSpeech panel
            self.engine_selection_widget.setVisible(False) # Hide engine selection
        else:
            self.engine_selection_widget.setVisible(True) # Show engine selection
            self.panel_voicevox.setVisible(engine == "VoiceVox")
            self.panel_elevenlabs.setVisible(engine == "ElevenLabs")
            self.panel_openai_tts.setVisible(engine == "OpenAI TTS")
            self.panel_aivisspeech.setVisible(engine == "AivisSpeech") # Show/hide AivisSpeech panel
            if engine == "AivisSpeech" and self.panel_aivisspeech.isVisible():
                # Optionally auto-load voices or prompt user
                # For now, user must click "Load Voices"
                pass

    def validate_elevenlabs_key(self):
        # Simple key validation for ElevenLabs
        key = self.elevenlabs_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Missing Key", "Please enter your ElevenLabs API key.")
            return
        try:
            r = requests.get("https://api.elevenlabs.io/v2/voices", headers={"xi-api-key": key}, timeout=10)
            r.raise_for_status()
            QMessageBox.information(self, "Key Valid", "ElevenLabs API key is valid.")
        except Exception as e:
            QMessageBox.critical(self, "Validation Failed", f"Key validation failed: {e}")

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
        # Ensure latest engine selection is used
        CONFIG["tts_engine"] = self.tts_engine_combo.currentText()
        try:
            # Try to connect to VOICEVOX with more detailed diagnostics
            is_running = check_voicevox_running()
            
            if is_running:
                # Try to generate a very small test audio to confirm full functionality
                test_text = "テスト"
                test_result = backend_generate_audio("", test_text)
                
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
                    "- Firewall is blocking connections to VOICEVOX\n\n"
                )
        except Exception as e:
            debug_log(f"Error during VOICEVOX connection test: {str(e)}")
            QMessageBox.critical(self, "Test Error", 
                "An error occurred while testing VOICEVOX connection")

    def test_aivisspeech_connection(self):
        """Test the connection to AivisSpeech and show detailed results"""
        # Ensure latest engine selection is used
        CONFIG["tts_engine"] = self.tts_engine_combo.currentText()
        try:
            # Directly use the imported function
            is_running = check_aivisspeech_running(base_url="http://127.0.0.1:10101")

            if is_running:
                QMessageBox.information(self, "AivisSpeech Connection Successful", 
                    "Successfully connected to AivisSpeech engine on http://127.0.0.1:10101.")
            else:
                QMessageBox.critical(self, "AivisSpeech Connection Failed", 
                    "Failed to connect to AivisSpeech engine on http://127.0.0.1:10101.\n\n"
                    "Please ensure AivisSpeech Engine is running and accessible.")
        except Exception as e:
            debug_log(f"Error during AivisSpeech connection test: {str(e)}")
            QMessageBox.critical(self, "Test Error", 
                f"An error occurred while testing AivisSpeech connection:\n\n{str(e)}")

    def load_aivisspeech_voices_ui(self):
        debug_log("Attempting to load AivisSpeech voices for UI...")
        voices = get_aivisspeech_voices() # Assumes base_url is default http://127.0.0.1:10101
        self.aivisspeech_voices_table.setRowCount(0) # Clear existing rows

        if voices is None:
            QMessageBox.warning(self, "Load Voices Failed", "Could not retrieve voices from AivisSpeech. Is it running?")
            return
        
        if not voices:
            QMessageBox.information(self, "No Voices Found", "AivisSpeech is running, but no voices were found.")
            return

        self.aivisspeech_voices_table.setRowCount(len(voices))
        for i, voice_info in enumerate(voices):
            speaker_name = voice_info.get('speaker_name', 'N/A')
            style_name = voice_info.get('style_name', 'N/A')
            style_id = voice_info.get('style_id')

            self.aivisspeech_voices_table.setItem(i, 0, QTableWidgetItem(speaker_name))
            self.aivisspeech_voices_table.setItem(i, 1, QTableWidgetItem(style_name))

            play_btn = QPushButton("Play")
            # Store style_id in the button itself or use a lambda with default argument
            play_btn.setProperty("style_id", style_id) 
            qconnect(play_btn.clicked, lambda checked=False, sid=style_id: self.play_aivisspeech_sample_ui(sid))
            self.aivisspeech_voices_table.setCellWidget(i, 2, play_btn)
            
            default_btn = QPushButton("Set Default")
            default_btn.setProperty("style_id", style_id)
            qconnect(default_btn.clicked, lambda checked=False, sid=style_id: self.set_aivisspeech_default_style(sid))
            self.aivisspeech_voices_table.setCellWidget(i, 3, default_btn)

        # Highlight currently selected default voice if it exists
        current_default_id = CONFIG.get("aivisspeech_style_id")
        if current_default_id is not None:
            for i in range(self.aivisspeech_voices_table.rowCount()):
                button_widget = self.aivisspeech_voices_table.cellWidget(i, 3)
                if button_widget and button_widget.property("style_id") == current_default_id:
                    self.aivisspeech_voices_table.selectRow(i) # Visually indicate
                    # You might want to change button text or style too
                    break
        debug_log(f"Displayed {len(voices)} AivisSpeech voices in table.")

    def play_aivisspeech_sample_ui(self, style_id):
        if style_id is None:
            QMessageBox.warning(self, "Play Sample Error", "No style ID provided for the sample.")
            return

        sample_text = "こんにちは。日本へようこそ。"
        debug_log(f"Playing AivisSpeech sample for style_id {style_id} with text: '{sample_text}'")

        # 1) Ask the TTS routine to save into collection.media
        sound_tag = backend_generate_audio(
            api_key=None,
            text=sample_text,
            engine_override="AivisSpeech",
            style_id_override=style_id,
            save_to_collection_override=True,
        )

        # 2) We expect a string like "[sound:voice_filename.wav]"
        if sound_tag and sound_tag.startswith("[sound:") and sound_tag.endswith("]"):
            filename = sound_tag[7:-1]  # strip off "[" and "]"
            debug_log(f"Sample audio saved to collection.media as: {filename}, playing now.")
            try:
                # 3) Play via Anki's built-in sound player
                from aqt.sound import play
                play(filename)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Playback Error",
                    f"Could not play audio sample: {e}"
                )
                debug_log(f"Error playing sample from media folder: {e}")
        else:
            # fallback if generation failed
            QMessageBox.critical(
                self,
                "Sample Generation Failed",
                "Could not generate audio sample from AivisSpeech."
            )
            debug_log("Failed to generate or find audio sample file.")

    def load_voicevox_voices_ui(self):
        debug_log("Loading VoiceVox voices into UI...")
        try:
            response = requests.get("http://127.0.0.1:50021/speakers", timeout=5)
            response.raise_for_status()
            speakers = response.json()
        except Exception as e:
            QMessageBox.warning(self, "Load Voices Failed",
                                f"Could not retrieve voices from VoiceVox: {e}")
            return

        # Build list of (speaker, style, style_id)
        voices = []
        for sp in speakers:
            name = sp.get("name", "Unknown")
            for st in sp.get("styles", []):
                voices.append((name, st.get("name", "Default"), st.get("id")))

        self.voicevox_voices_table.setRowCount(len(voices))
        for row, (name, style_name, style_id) in enumerate(voices):
            self.voicevox_voices_table.setItem(row, 0, QTableWidgetItem(name))
            self.voicevox_voices_table.setItem(row, 1, QTableWidgetItem(style_name))

            # Play button
            play_btn = QPushButton("Play")
            qconnect(play_btn.clicked, lambda _, sid=style_id: self.play_voicevox_sample_ui(sid))
            self.voicevox_voices_table.setCellWidget(row, 2, play_btn)

            # Set Default button
            default_btn = QPushButton("Set Default")
            default_btn.setProperty("style_id", style_id)
            qconnect(default_btn.clicked, lambda _, sid=style_id: self.set_voicevox_default_style(sid))
            self.voicevox_voices_table.setCellWidget(row, 3, default_btn)

        # Highlight existing default style
        current = CONFIG.get("voicevox_style_id")
        if current is not None:
            for r in range(self.voicevox_voices_table.rowCount()):
                btn = self.voicevox_voices_table.cellWidget(r, 3)
                if btn and btn.property("style_id") == current:
                    self.voicevox_voices_table.selectRow(r)
                    break

    def play_voicevox_sample_ui(self, speaker_id):
        sample_text = "こんにちは。日本へようこそ。"
        debug_log(f"Playing VoiceVox sample for speaker_id {speaker_id} with text: '{sample_text}'")
        # Generate and save into collection.media
        result = backend_generate_audio(
            api_key=None,
            text=sample_text,
            engine_override="VoiceVox",
            save_to_collection_override=True
        )
        if result:
            # result may be a sound tag or a direct file path
            if result.startswith("[sound:") and result.endswith("]"):
                filename = result[7:-1]  # strip off the sound tag brackets
            else:
                filename = os.path.basename(result)

            debug_log(f"Sample audio saved as: {filename}, playing now.")
            try:
                from aqt.sound import play
                play(filename)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Playback Error",
                    f"Could not play audio sample: {e}"
                )
                debug_log(f"Error playing VoiceVox sample from media folder: {e}")
        else:
            QMessageBox.critical(
                self,
                "Sample Generation Failed",
                "Could not generate audio sample from VoiceVox."
            )
            debug_log("Failed to generate VoiceVox sample.")

    def set_aivisspeech_default_style(self, style_id):
        self.selected_aivisspeech_style_id = style_id
        CONFIG["aivisspeech_style_id"] = style_id # Also update live CONFIG
        QMessageBox.information(self, "Default Voice Set", f"AivisSpeech voice style ID {style_id} has been set as the default for new generations.")
        # Re-highlight or update UI
        self.aivisspeech_voices_table.clearSelection()
        for i in range(self.aivisspeech_voices_table.rowCount()):
            button_widget = self.aivisspeech_voices_table.cellWidget(i, 3) # Check the "Set Default" button
            if button_widget and button_widget.property("style_id") == style_id:
                self.aivisspeech_voices_table.selectRow(i)
                # Optionally, change button text to "Current Default" or disable it
                break
        debug_log(f"AivisSpeech default style ID set to: {style_id}")

    def set_voicevox_default_style(self, style_id):
        CONFIG["voicevox_style_id"] = style_id
        QMessageBox.information(self, "Default Style Set",
                                f"VoiceVox style ID {style_id} has been set as the default.")
        self.voicevox_voices_table.clearSelection()
        for i in range(self.voicevox_voices_table.rowCount()):
            btn = self.voicevox_voices_table.cellWidget(i, 3)
            if btn and btn.property("style_id") == style_id:
                self.voicevox_voices_table.selectRow(i)
                break

    def open_language_learning_community(self):
        """Open the Matt vs Japan language learning community URL in the default browser"""
        try:
            webbrowser.open("https://www.skool.com/mattvsjapan/about?ref=837f80b041cf40e9a3979cd1561a67b2")
            debug_log("Opened language learning community URL in browser")
        except Exception as e:
            debug_log(f"Error opening language learning community URL: {str(e)}")
            QMessageBox.warning(self, "Error", f"Could not open the webpage. Please visit:\nhttps://www.skool.com/mattvsjapan/about?ref=837f80b041cf40e9a3979cd1561a67b2")

# Process a single note with debug mode
def process_note_debug(note, generate_text, generate_audio, override_text, override_audio, progress_callback=None):
    """
    Process a note to generate text explanations and/or audio based on user preferences.
    
    This function implements a 4-checkbox system:
    1. generate_text: Whether user wants to generate explanation text
    2. generate_audio: Whether user wants to generate explanation audio  
    3. override_text: Whether to override existing explanation text (only shown if content exists)
    4. override_audio: Whether to override existing explanation audio (only shown if content exists)
    
    Logic Flow:
    - Text is generated if: user wants it AND (field is empty OR override requested) AND feature not disabled
    - Audio is generated if: user wants it AND (field is empty OR override requested) AND feature not disabled
    - If nothing needs generation, the function exits early with appropriate reasoning
    
    Args:
        note: The Anki note to process
        generate_text: Boolean - whether to generate explanation text
        generate_audio: Boolean - whether to generate explanation audio
        override_text: Boolean - whether to override existing explanation text
        override_audio: Boolean - whether to override existing explanation audio  
        progress_callback: Optional function to call with progress updates
        
    Returns:
        tuple: (success: bool, message: str) indicating result and details
    """
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    debug_log_path = os.path.join(addon_dir, "process_debug.txt")
    
    debug_log("=== PROCESS NOTE START ===")
    debug_log(f"Note ID: {note.id}")
    
    try:
        if not CONFIG["openai_key"]:
            debug_log("No API key set")
            return False, "No OpenAI API key set. Please set your API key in the settings."

        # Extract data from note
        debug_log("Extracting data from note")
        word = note[CONFIG["word_field"]] if CONFIG["word_field"] in note else ""
        sentence = note[CONFIG["sentence_field"]] if CONFIG["sentence_field"] in note else ""
        definition = note[CONFIG["definition_field"]] if CONFIG["definition_field"] in note else ""
        debug_log(f"Word field: {CONFIG['word_field']} = {word[:30]}...")
        debug_log(f"Sentence field: {CONFIG['sentence_field']} = {sentence[:30]}...")
        debug_log(f"Definition field: {CONFIG['definition_field']} = {definition[:30]}...")
        
        # Check if text generation is disabled in settings
        text_generation_disabled = CONFIG.get("disable_text_generation", False)
        debug_log(f"Text generation disabled: {text_generation_disabled}")
        
        # === STEP 1: Check current field states ===
        # Check what content currently exists in the target fields
        explanation_exists = CONFIG["explanation_field"] in note and note[CONFIG["explanation_field"]].strip()
        audio_exists = CONFIG["explanation_audio_field"] in note and note[CONFIG["explanation_audio_field"]].strip()
        
        debug_log(f"=== FIELD STATE ANALYSIS ===")
        debug_log(f"Explanation field '{CONFIG['explanation_field']}' exists: {explanation_exists}")
        debug_log(f"Audio field '{CONFIG['explanation_audio_field']}' exists: {audio_exists}")
        
        # === STEP 2: Log user's checkbox selections ===
        debug_log(f"=== USER CHECKBOX SELECTIONS ===")
        debug_log(f"Generate Text checkbox: {generate_text}")
        debug_log(f"Generate Audio checkbox: {generate_audio}")  
        debug_log(f"Override Text checkbox: {override_text}")
        debug_log(f"Override Audio checkbox: {override_audio}")
        
        # === STEP 3: Check system settings ===
        debug_log(f"=== SYSTEM SETTINGS ===")
        debug_log(f"Text generation disabled: {text_generation_disabled}")
        debug_log(f"Audio generation disabled: {CONFIG.get('disable_audio', False)}")
        
        # === STEP 4: Determine what should be generated ===
        # 
        # Core Logic for Generation Decision:
        # For each content type (text/audio), we generate if ALL three conditions are met:
        # 1. User wants generation (checkbox checked)
        # 2. Content is needed (field is empty OR user explicitly wants to override existing content)
        # 3. Feature is allowed (not disabled in settings)
        #
        # This ensures that:
        # - Empty fields get auto-generated when user requests generation
        # - Existing content is preserved unless user explicitly chooses to override
        # - Disabled features are respected regardless of user choices
        debug_log(f"=== GENERATION DECISION LOGIC ===")
        
        # Text decision breakdown
        text_user_wants = generate_text  # Did user check "Generate Text"?
        text_needed = not explanation_exists or override_text  # Is text needed? (empty OR override requested)
        text_allowed = not text_generation_disabled  # Is text generation enabled in settings?
        should_generate_text = text_user_wants and text_needed and text_allowed
        
        debug_log(f"TEXT DECISION:")
        debug_log(f"  User wants text generation: {text_user_wants}")
        debug_log(f"  Text needed (empty field OR override requested): {text_needed}")
        debug_log(f"    - Field is empty: {not explanation_exists}")
        debug_log(f"    - Override requested: {override_text}")
        debug_log(f"  Text generation allowed (not disabled): {text_allowed}")
        debug_log(f"  FINAL TEXT DECISION: {should_generate_text}")
        
        # Audio decision breakdown  
        audio_user_wants = generate_audio  # Did user check "Generate Audio"?
        audio_needed = not audio_exists or override_audio  # Is audio needed? (empty OR override requested)
        audio_allowed = not CONFIG.get("disable_audio", False)  # Is audio generation enabled in settings?
        should_generate_audio = audio_user_wants and audio_needed and audio_allowed
        
        debug_log(f"AUDIO DECISION:")
        debug_log(f"  User wants audio generation: {audio_user_wants}")
        debug_log(f"  Audio needed (empty field OR override requested): {audio_needed}")
        debug_log(f"    - Field is empty: {not audio_exists}")
        debug_log(f"    - Override requested: {override_audio}")
        debug_log(f"  Audio generation allowed (not disabled): {audio_allowed}")
        debug_log(f"  FINAL AUDIO DECISION: {should_generate_audio}")
        
        # === STEP 5: Early exit check ===
        debug_log(f"=== EARLY EXIT CHECK ===")
        if not should_generate_text and not should_generate_audio:
            debug_log("EARLY EXIT: Nothing to generate")
            debug_log(f"Reason: should_generate_text={should_generate_text}, should_generate_audio={should_generate_audio}")
            
            # Provide more specific feedback about why nothing was generated
            reasons = []
            if not text_user_wants and not audio_user_wants:
                reasons.append("no generation requested")
            elif text_generation_disabled and CONFIG.get("disable_audio", False):
                reasons.append("both text and audio generation disabled in settings")
            elif explanation_exists and not override_text and audio_exists and not override_audio:
                reasons.append("content already exists and no override requested")
            elif explanation_exists and not override_text:
                reasons.append("text content already exists and text override not requested")
            elif audio_exists and not override_audio:
                reasons.append("audio content already exists and audio override not requested")
            else:
                reasons.append("generation conditions not met")
            
            reason_text = ", ".join(reasons)
            debug_log(f"Early exit reason: {reason_text}")
            return True, f"Skipped: {reason_text}"
        
        debug_log(f"PROCEEDING: At least one type of generation is needed")
        debug_log(f"Will generate text: {should_generate_text}")
        debug_log(f"Will generate audio: {should_generate_audio}")
        
        # Process with OpenAI (only if text generation is needed)
        explanation = None
        if should_generate_text:
            debug_log("Text generation needed - preparing prompt for OpenAI")
            try:
                prompt = CONFIG["gpt_prompt"].format(
                    word=word,
                    sentence=sentence,
                    definition=definition
                )
            except KeyError as e:
                debug_log(f"KeyError in prompt formatting: {str(e)}")
                debug_log(f"Prompt template: {CONFIG['gpt_prompt']}")
                debug_log(f"Available variables: word='{word}', sentence='{sentence}', definition='{definition}'")
                return False, f"Error in prompt template: missing placeholder {str(e)}"
            
            debug_log("Calling process_with_openai")
            try:
                if progress_callback and callable(progress_callback):
                    progress_callback("Sending request to OpenAI...")
                    
                explanation = process_with_openai(CONFIG["openai_key"], prompt, CONFIG["openai_model"])
                if not explanation:
                    debug_log("Failed to generate explanation from OpenAI")
                    return False, "Failed to generate explanation from OpenAI"
                debug_log(f"Received explanation: {explanation[:50]}...")
                
                if progress_callback and callable(progress_callback):
                    progress_callback("Received explanation from OpenAI")
            except Exception as e:
                debug_log(f"Error in process_with_openai: {str(e)}")
                return False, f"Error calling OpenAI API: {str(e)}"
        else:
            debug_log("Text generation not needed - using existing content for audio generation")
            # Use existing explanation for audio generation if available
            if CONFIG["explanation_field"] in note and note[CONFIG["explanation_field"]].strip():
                explanation = note[CONFIG["explanation_field"]]
                debug_log("Using existing explanation text for audio generation")
            else:
                # Use word for audio generation if no explanation exists
                explanation = word if word else "テスト"
                debug_log(f"No existing explanation, using word for audio: {explanation}")
            
            if progress_callback and callable(progress_callback):
                progress_callback("Using existing content for audio generation")
        
        # Save explanation to note (only if text generation was performed and we have new content)
        if should_generate_text and CONFIG["explanation_field"] in note:
            debug_log(f"Saving newly generated explanation to field: {CONFIG['explanation_field']}")
            try:
                note[CONFIG["explanation_field"]] = explanation
                debug_log("Newly generated explanation saved to note")
                
                if progress_callback and callable(progress_callback):
                    progress_callback("Explanation saved to note")
            except Exception as e:
                debug_log(f"Error setting explanation field: {CONFIG['explanation_field']}: {str(e)}")
                return False, f"Error saving explanation to note: {str(e)}"
        elif not should_generate_text:
            debug_log("Text generation not performed, skipping explanation field update")
        
        # Also try the "explanation" field (with correct spelling) if it exists (only if text generation was performed)
        if should_generate_text and "explanation" in note and CONFIG["explanation_field"] != "explanation":
            debug_log("Also saving newly generated explanation to 'explanation' field (correct spelling)")
            try:
                note["explanation"] = explanation
                debug_log("Explanation saved to note (correct spelling field)")
            except Exception as e:
                debug_log(f"Error setting explanation field (correct spelling): {str(e)}")
                # Continue even if this fails
        
        # Audio generation using the selected TTS engine
        debug_log("Starting audio generation step")
        audio_path_result = [None]
        
        # Check if audio generation should be performed
        if should_generate_audio:
            debug_log("Audio generation needed - proceeding with TTS")
            # Only generate if the audio field exists
            if CONFIG["explanation_audio_field"] in note:
                debug_log(f"Audio field found: {CONFIG['explanation_audio_field']}")
                try:
                    # Update progress callback
                    if progress_callback and callable(progress_callback):
                        progress_callback(f"Generating audio with {CONFIG['tts_engine']}...")
                    # Generate audio using the explanation text (existing or newly generated)
                    debug_log(f"Calling generate_audio with engine: {CONFIG['tts_engine']}")
                    debug_log(f"Audio generation parameters: api_key_length={len(CONFIG.get('openai_key', ''))}, explanation_length={len(explanation)}")
                    
                    # Prepare parameters for audio generation with detailed logging
                    api_key = CONFIG.get("openai_key", "")
                    aivis_style_id = CONFIG.get("aivisspeech_style_id") if CONFIG['tts_engine'] == 'AivisSpeech' else None
                    voicevox_speaker_id = CONFIG.get("voicevox_default_speaker_id") if CONFIG['tts_engine'] == 'VoiceVox' else None
                    
                    debug_log(f"Calling generate_audio with: api_key='{api_key[:10] if api_key else 'None'}...', text_length={len(explanation)}, aivis_style_id={aivis_style_id}, voicevox_speaker_id={voicevox_speaker_id}")
                    
                    audio_path = backend_generate_audio(
                        api_key,
                        explanation,
                        style_id_override=aivis_style_id,
                        speaker_id_override=voicevox_speaker_id
                    )
                    if audio_path:
                        debug_log(f"Audio generated successfully: {audio_path}")
                        audio_path_result[0] = audio_path
                except Exception as e:
                    debug_log(f"Error during audio generation: {str(e)}")
                
                # Save audio result to note if generation was successful
                if audio_path_result[0]:
                    # If the returned value is already an Anki sound tag, use it as-is,
                    # otherwise wrap the filename in one. This prevents double "[sound:" tags
                    if str(audio_path_result[0]).startswith("[sound:") and str(audio_path_result[0]).endswith("]"):
                        note[CONFIG["explanation_audio_field"]] = audio_path_result[0]
                    else:
                        audio_filename = os.path.basename(audio_path_result[0])
                        note[CONFIG["explanation_audio_field"]] = f"[sound:{audio_filename}]"
                    debug_log("Audio reference saved to note")
                else:
                    # Audio generation failed - add placeholder
                    note[CONFIG["explanation_audio_field"]] = "[Audio generation failed]"
                    debug_log("Audio generation failed, placeholder saved")
            else:
                debug_log(f"Audio field not found in note: {CONFIG['explanation_audio_field']}")
        
        elif CONFIG.get("disable_audio", False):
            debug_log("Audio generation is disabled in settings - leaving audio field unchanged")
            # Don't modify the audio field when audio generation is disabled
        else:
            debug_log("Audio generation not needed - leaving audio field unchanged")
            # Don't modify the audio field when audio override is not requested
        
        # Also handle the "explanationAudio" field (with correct spelling) if it exists
        if should_generate_audio and "explanationAudio" in note and CONFIG["explanation_audio_field"] != "explanationAudio":
            debug_log("Also updating 'explanationAudio' field (correct spelling)")
            if audio_path_result[0]:
                # If the returned value is already an Anki sound tag, use it as-is,
                # otherwise wrap the filename in one. This prevents double "[sound:" tags
                if str(audio_path_result[0]).startswith("[sound:") and str(audio_path_result[0]).endswith("]"):
                    note["explanationAudio"] = audio_path_result[0]
                else:
                    audio_filename = os.path.basename(audio_path_result[0])
                    note["explanationAudio"] = f"[sound:{audio_filename}]"
                debug_log("Audio reference saved to explanationAudio field (correct spelling)")
            else:
                note["explanationAudio"] = "[Audio generation failed]"
                debug_log("Audio generation failed, setting placeholder in explanationAudio field")
        
        # Save changes - wrap in try/except to catch any issues
        try:
            debug_log("Calling note.flush() to save changes")
            
            if progress_callback and callable(progress_callback):
                progress_callback("Saving changes to note...")
                
            note.flush()
            debug_log("Note.flush() completed successfully")
            
            if progress_callback and callable(progress_callback):
                progress_callback("Changes saved successfully")
        except Exception as e:
            debug_log(f"Error in note.flush(): {str(e)}")
            return False, f"Error saving changes to note: {str(e)}"
            
        debug_log("=== PROCESS NOTE COMPLETED SUCCESSFULLY ===")
        return True, "Process completed successfully"
    except Exception as e:
        debug_log(f"Unexpected error in process_note: {str(e)}")
        debug_log(f"Stack trace: {traceback.format_exc()}")
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
        progress.setWindowTitle("AI Language Explainer")
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
                debug_log("Failed to set window modality - Qt version compatibility issue")
                
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
        
        # Show the generation options dialog  
        generation_dialog = BulkGenerationDialog(mw, [note.id])
        generation_dialog.setWindowTitle("AI Language Explainer - Generation Options")
        if generation_dialog.exec() != QDialog.DialogCode.Accepted:
            debug_log("User canceled generation dialog")
            progress.cancel()
            return
        
        # Get the generation options from the dialog (4 values: generate_text, generate_audio, override_text, override_audio)
        generate_text, generate_audio, override_text, override_audio = generation_dialog.get_generation_options()
        debug_log(f"Generation options: generate_text={generate_text}, generate_audio={generate_audio}, override_text={override_text}, override_audio={override_audio}")
        
        # Store generation flags for backend processing
        CONFIG["generate_text"] = generate_text
        CONFIG["generate_audio"] = generate_audio
        CONFIG["override_text"] = override_text
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
                    debug_log(f"Processing timeout after {elapsed_time:.1f} seconds")
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
                debug_log(f"Error in handle_timeout: {str(e)}")
        
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
                        debug_log(f"Progress update: {message}, value: {progress_value}")
                    elif "explanation saved to note" in message:
                        progress_value = 75
                        debug_log(f"Progress update: {message}, value: {progress_value}")
                    elif "Generating audio" in message:
                        progress_value = 80
                        debug_log(f"Progress update: {message}, value: {progress_value}")
                    elif "Audio generated" in message:
                        progress_value = 90
                        debug_log(f"Progress update: {message}, value: {progress_value}")
                    elif "Audio generation failed" in message or "Error generating audio" in message:
                        progress_value = 85
                        debug_log(f"Progress update: {message}, value: {progress_value}")
                    elif "VOICEVOX not running" in message:
                        progress_value = 85
                        debug_log(f"Progress update: {message}, value: {progress_value}")
                    elif "Saving changes" in message:
                        progress_value = 95
                        debug_log(f"Progress update: {message}, value: {progress_value}")
                    elif "Changes saved successfully" in message:
                        progress_value = 98
                        debug_log(f"Progress update: {message}, value: {progress_value}")
                    
                    # Force UI update on main thread
                    def update_ui():
                        update_progress_ui(message, progress_value)
                    mw.taskman.run_on_main(update_ui)
                
                def update_progress_ui(message, value):
                    try:
                        if progress.wasCanceled():
                            debug_log("Progress dialog was canceled, skipping update")
                            return
                            
                        progress.setValue(value)
                        progress.setLabelText(message)
                        QApplication.processEvents()
                        debug_log(f"UI updated: {message}, value: {value}")
                    except Exception as e:
                        debug_log(f"Error updating progress UI: {str(e)}")
                
                # Call process_note with the progress callback
                debug_log("Starting process_note with progress callback")
                result, message = process_note(note, generate_text, generate_audio, override_text, override_audio, update_progress)
                debug_log(f"process_note completed with result: {result}, message: {message}")
                
                # Mark processing as completed to stop the timeout checker
                processing_completed[0] = True
                
                # Update UI on the main thread
                mw.taskman.run_on_main(lambda: handle_process_result(result, message, card, progress))
            except Exception as e:
                # Mark processing as completed to stop the timeout checker
                processing_completed[0] = True
                
                error_msg = str(e)
                debug_log(f"Error in process_with_progress: {str(e)}")
                mw.taskman.run_on_main(lambda: 
                    show_error(error_msg, progress))
        
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
                        debug_log(f"Error in card.load(): {str(e)}")
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
                debug_log(f"Error in handle_process_result: {str(e)}")
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
                debug_log(f"Error in show_error: {str(e)}")
                tooltip(f"Error: {error_msg}")
        
        # Start processing in a separate thread
        threading.Thread(target=process_with_progress).start()
        
    except Exception as e:
        debug_log(f"Unexpected error in process_current_card: {str(e)}")
        tooltip("An error occurred. Check the error log for details.")

# Add the button to the card during review
def add_button_to_reviewer():
    try:
        debug_log("Adding button to reviewer")
        
        # Get reviewer bottombar element
        bottombar = mw.reviewer.bottom.web
        
        # Create JavaScript code to add button
        js = """
        (function() {
            console.log('Running AI Language Explainer button script');
            
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
            
            console.log('AI Language Explainer button added successfully');
        })();
        """
        
        # Inject JavaScript code
        bottombar.eval(js)
        debug_log("JavaScript injected to add button")
    except Exception as e:
        debug_log(f"Error adding button to reviewer: {str(e)}")
        debug_log(traceback.format_exc())

# Set up the hook to add the button when a card is shown
def on_card_shown(card=None):
    try:
        # Log for debugging
        debug_log(f"on_card_shown called with card: {card}")
        
        # Check if button is hidden in settings
        if CONFIG.get("hide_button", False):
            debug_log("Button is hidden in settings, skipping button addition")
            return
        
        # Only add the button when the answer is shown
        if mw.state != "review":
            debug_log("Not in review state, skipping button addition")
            return
            
        if not mw.reviewer.card:
            debug_log("No card in reviewer, skipping button addition")
            return
            
        if not mw.reviewer.state == "answer":
            debug_log("Not showing answer, skipping button addition")
            return
        
        # Use the card parameter if provided, otherwise fall back to mw.reviewer.card
        current_card = card if card else mw.reviewer.card
        debug_log(f"Current card ID: {current_card.id}")
        
        # Get the note type
        note_type_name = current_card.note().note_type()["name"]
        debug_log(f"Note type: {note_type_name}, Config note type: {CONFIG['note_type']}")
        
        if note_type_name == CONFIG["note_type"]:
            debug_log("Note type matches, adding button")
            add_button_to_reviewer()
        else:
            debug_log(f"Note type doesn't match, skipping button addition")
    except Exception as e:
        debug_log(f"Error in on_card_shown: {str(e)}")
        debug_log(traceback.format_exc())

# Handle reviewer commands
def on_js_message(handled, message, context):
    # Log the message for debugging
    debug_log(f"Received message: {message}, handled: {handled}, context: {context}")
    
    # In Anki 25, the message might be a tuple or a string
    cmd = None
    if isinstance(message, tuple):
        cmd = message[0]
    else:
        cmd = message
    
    # Check if this is our command
    if cmd == "gpt_explanation":
        debug_log("Recognized gpt_explanation command, processing...")
        process_current_card()
        
        # Try to detect Anki version to return appropriate value
        try:
            import anki
            anki_version = int(anki.buildinfo.version.split('.')[0])
            debug_log(f"Anki version: {anki_version}")
            if anki_version >= 25:
                debug_log("Returning (True, None) for Anki 25+")
                return (True, None)
            else:
                debug_log("Returning True for older Anki")
                return True
        except Exception as e:
            debug_log(f"Error detecting Anki version: {e}")
            # If we can't determine version, return a tuple which works in Anki 25
            return (True, None)
    
    return handled

# Set up menu items
def setup_menu():
    # Create main menu for AI Language Explainer
    ai_explainer_menu = QMenu("AI Language Explainer", mw)
    
    # Add settings as a submenu option
    settings_action = QAction("Settings", mw)
    qconnect(settings_action.triggered, open_settings)
    ai_explainer_menu.addAction(settings_action)
    
    # Add the menu to the Tools menu
    mw.form.menuTools.addMenu(ai_explainer_menu)
    
    # Enable browser menu action for bulk processing
    debug_log("Registering browser_menus_did_init hook for batch processing")
    gui_hooks.browser_menus_did_init.append(setup_browser_menu)
    debug_log("Browser hook registered")

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
        showInfo("Please set your OpenAI API key in the AI Language Explainer Settings.")
        return
    
    # Show the bulk generation options dialog with selected notes for analysis
    bulk_dialog = BulkGenerationDialog(mw, selected_notes)
    if bulk_dialog.exec() != QDialog.DialogCode.Accepted:
        debug_log("User canceled bulk generation dialog")
        return
    
    # Get the generation options from the dialog (4 values: generate_text, generate_audio, override_text, override_audio)
    generate_text, generate_audio, override_text, override_audio = bulk_dialog.get_generation_options()
    debug_log(f"Bulk generation options: generate_text={generate_text}, generate_audio={generate_audio}, override_text={override_text}, override_audio={override_audio}")
    
    # Store generation flags for backend processing
    CONFIG["generate_text"] = generate_text
    CONFIG["generate_audio"] = generate_audio
    CONFIG["override_text"] = override_text
    CONFIG["override_audio"] = override_audio
    
    # Create a progress dialog with fixed width to avoid the resizing issue
    progress = QProgressDialog("Processing cards...", "Cancel", 0, len(selected_notes) + 1, mw)
    progress.setWindowTitle("AI Language Explainer Batch Processing")
    
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
            debug_log("Failed to set window modality - Qt version compatibility issue")
            
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
                    debug_log(f"Skipping note {note_id}: Note type {model_name} doesn't match configured type {CONFIG['note_type']}")
                    missing_fields_count += 1
                    continue
                
                # Skip processing if required fields are missing
                required_fields = [CONFIG["word_field"], CONFIG["sentence_field"], CONFIG["definition_field"]]
                if not all(field in note and field in note.keys() for field in required_fields):
                    debug_log(f"Skipping note {note_id}: Missing required fields")
                    missing_fields_count += 1
                    continue
                
                # Process the note with separate generation flags
                success, message = process_note_debug(note, generate_text, generate_audio, override_text, override_audio, progress_callback=None)
                if success:
                    # Check for different skip messages that were updated
                    if "already exists" in message or "not requested" in message:
                        skipped_count += 1
                        debug_log(f"Note {note_id} skipped: {message}")
                    else:
                        success_count += 1
                        debug_log(f"Note {note_id} processed successfully: {message}")
                        # Save changes to the database
                        note.flush()
                else:
                    error_count += 1
                    debug_log(f"Note {note_id} failed: {message}")
            
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
            debug_log(f"Error in batch processing: {str(e)}")
            debug_log(traceback.format_exc())
            mw.taskman.run_on_main(lambda: 
                showInfo(f"Error in batch processing: {str(e)}"))
        finally:
            mw.taskman.run_on_main(lambda: progress.hide())
    
    # Start processing thread
    threading.Thread(target=process_notes_thread, daemon=True).start()

# Add browser menu action for bulk processing
def setup_browser_menu(browser):
    debug_log("Setting up browser menu for batch processing")
    
    # Test if we can access the menu
    if hasattr(browser.form, 'menuEdit'):
        debug_log("Browser has menuEdit attribute")
    else:
        debug_log("Browser does NOT have menuEdit attribute - trying alternative approach")
        # Backwards compatibility with different Anki versions
        try:
            # Try to find the Edit menu by name
            for menu in browser.form.menubar.findChildren(QMenu):
                if menu.title() == "Edit":
                    debug_log("Found Edit menu by title")
                    action = QAction("Batch Generate AI Explanations", browser)
                    qconnect(action.triggered, batch_process_notes)
                    menu.addSeparator()
                    menu.addAction(action)
                    debug_log("Action added to Edit menu found by title")
                    return
        except Exception as e:
            debug_log(f"Error finding Edit menu: {str(e)}")
    
    # Original implementation
    try:
        action = QAction("Batch Generate AI Explanations", browser)
        qconnect(action.triggered, batch_process_notes)
        browser.form.menuEdit.addSeparator()
        browser.form.menuEdit.addAction(action)
        debug_log("Browser menu setup complete")
    except Exception as e:
        debug_log(f"Error setting up browser menu: {str(e)}")
        
        # Try adding to a different menu as fallback
        try:
            debug_log("Trying to add to Tools menu instead")
            action = QAction("Batch Generate AI Explanations", browser)
            qconnect(action.triggered, batch_process_notes)
            browser.form.menuTools.addSeparator()
            browser.form.menuTools.addAction(action)
            debug_log("Added action to Tools menu as fallback")
        except Exception as e2:
            debug_log(f"Error adding to Tools menu: {str(e2)}")

# Initialize the add-on
def init():
    try:
        debug_log("Initializing AI Language Explainer addon")
        
        # Load configuration
        load_config()
        debug_log(f"Configuration loaded: {CONFIG}")
        
        # Set up menu
        setup_menu()
        debug_log("Menu setup complete")
        
        # Register hooks
        debug_log("Registering hooks")
        
        # Only need to hook into the answer shown event
        gui_hooks.reviewer_did_show_answer.append(on_card_shown)
        debug_log("Registered reviewer_did_show_answer hook")
        
        # Register the message handler
        gui_hooks.webview_did_receive_js_message.append(on_js_message)
        debug_log("Registered webview_did_receive_js_message hook")
        
        debug_log("AI Language Explainer addon initialization complete")
    except Exception as e:
        debug_log(f"Error during initialization: {str(e)}")
        debug_log(traceback.format_exc())

# Run initialization
init()