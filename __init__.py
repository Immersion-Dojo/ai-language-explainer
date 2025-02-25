# File: __init__.py
from aqt import mw, gui_hooks
from aqt.utils import qconnect, showInfo, tooltip, askUser
from aqt.qt import QAction, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QLineEdit, QProgressDialog, QCheckBox, QMessageBox, QApplication, Qt
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
        tooltip("Installing required dependencies for GPT Explanation addon...")
        
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
from .api_handler import process_with_openai, generate_audio, check_voicevox_running

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
    "picture_field": "",
    "explanation_field": "",
    "explanation_audio_field": "",  # Kept for backward compatibility
    "api_key": "",
    "gpt_prompt": "Please write an example sentence using the word '{word}' in the context of the original sentence: '{sentence}'. The definition of the word is: '{definition}'. Create an explanation that helps a Japanese language learner understand how this word is used."
}

# Load configuration
def load_config():
    global CONFIG
    config = mw.addonManager.getConfig(__name__)
    if config:
        CONFIG.update(config)

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
        self.setWindowTitle("GPT Explanation Settings")
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Note Type Selection
        note_type_layout = QHBoxLayout()
        note_type_label = QLabel("Note Type:")
        self.note_type_combo = QComboBox()
        self.note_type_combo.addItems(get_note_types())
        self.note_type_combo.currentIndexChanged.connect(self.update_field_combos)
        note_type_layout.addWidget(note_type_label)
        note_type_layout.addWidget(self.note_type_combo)
        layout.addLayout(note_type_layout)

        # Input Fields
        layout.addWidget(QLabel("<b>Input Fields:</b>"))
        
        word_field_layout = QHBoxLayout()
        word_field_label = QLabel("Word Field:")
        self.word_field_combo = QComboBox()
        word_field_layout.addWidget(word_field_label)
        word_field_layout.addWidget(self.word_field_combo)
        layout.addLayout(word_field_layout)
        
        sentence_field_layout = QHBoxLayout()
        sentence_field_label = QLabel("Sentence Field:")
        self.sentence_field_combo = QComboBox()
        sentence_field_layout.addWidget(sentence_field_label)
        sentence_field_layout.addWidget(self.sentence_field_combo)
        layout.addLayout(sentence_field_layout)
        
        definition_field_layout = QHBoxLayout()
        definition_field_label = QLabel("Definition Field:")
        self.definition_field_combo = QComboBox()
        definition_field_layout.addWidget(definition_field_label)
        definition_field_layout.addWidget(self.definition_field_combo)
        layout.addLayout(definition_field_layout)
        
        picture_field_layout = QHBoxLayout()
        picture_field_label = QLabel("Picture Field:")
        self.picture_field_combo = QComboBox()
        picture_field_layout.addWidget(picture_field_label)
        picture_field_layout.addWidget(self.picture_field_combo)
        layout.addLayout(picture_field_layout)
        
        # Output Fields
        layout.addWidget(QLabel("<b>Output Fields:</b>"))
        
        explanation_field_layout = QHBoxLayout()
        explanation_field_label = QLabel("Explanation Field:")
        self.explanation_field_combo = QComboBox()
        explanation_field_layout.addWidget(explanation_field_label)
        explanation_field_layout.addWidget(self.explanation_field_combo)
        layout.addLayout(explanation_field_layout)
        
        # Audio field
        explanation_audio_field_layout = QHBoxLayout()
        explanation_audio_field_label = QLabel("Explanation Audio Field:")
        self.explanation_audio_field_combo = QComboBox()
        explanation_audio_field_layout.addWidget(explanation_audio_field_label)
        explanation_audio_field_layout.addWidget(self.explanation_audio_field_combo)
        layout.addLayout(explanation_audio_field_layout)
        
        # VOICEVOX notice
        voicevox_status = "Running" if check_voicevox_running() else "Not Running"
        voicevox_label = QLabel(f"<b>VOICEVOX Status: {voicevox_status}</b>")
        layout.addWidget(voicevox_label)
        
        voicevox_notice = QLabel("Note: Audio generation requires VOICEVOX to be running. Please download and start VOICEVOX before generating audio.")
        layout.addWidget(voicevox_notice)
        
        # API Key
        api_key_layout = QHBoxLayout()
        api_key_label = QLabel("OpenAI API Key:")
        self.api_key_input = QLineEdit()
        # Fix for newer PyQt versions - use the enum value directly
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_key_layout.addWidget(api_key_label)
        api_key_layout.addWidget(self.api_key_input)
        layout.addLayout(api_key_layout)
        
        # GPT Prompt
        layout.addWidget(QLabel("GPT Prompt:"))
        self.gpt_prompt_input = QLineEdit()
        layout.addWidget(self.gpt_prompt_input)
        
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
                      self.definition_field_combo, self.picture_field_combo,
                      self.explanation_field_combo, self.explanation_audio_field_combo]:
            current_text = combo.currentText()
            combo.clear()
            combo.addItems(fields)
            if current_text in fields:
                combo.setCurrentText(current_text)

    def load_settings(self):
        load_config()
        
        # Set values based on config
        if CONFIG["note_type"] in get_note_types():
            self.note_type_combo.setCurrentText(CONFIG["note_type"])
        
        # Update field combos based on selected note type
        self.update_field_combos()
        
        # Set field values
        field_combos = {
            "word_field": self.word_field_combo,
            "sentence_field": self.sentence_field_combo,
            "definition_field": self.definition_field_combo,
            "picture_field": self.picture_field_combo,
            "explanation_field": self.explanation_field_combo,
            "explanation_audio_field": self.explanation_audio_field_combo
        }
        
        for field_name, combo in field_combos.items():
            if CONFIG[field_name] and CONFIG[field_name] in [combo.itemText(i) for i in range(combo.count())]:
                combo.setCurrentText(CONFIG[field_name])
        
        # Set API key and prompt
        self.api_key_input.setText(CONFIG["api_key"])
        self.gpt_prompt_input.setText(CONFIG["gpt_prompt"])

    def save_and_close(self):
        # Update config with dialog values
        CONFIG["note_type"] = self.note_type_combo.currentText()
        CONFIG["word_field"] = self.word_field_combo.currentText()
        CONFIG["sentence_field"] = self.sentence_field_combo.currentText()
        CONFIG["definition_field"] = self.definition_field_combo.currentText()
        CONFIG["picture_field"] = self.picture_field_combo.currentText()
        CONFIG["explanation_field"] = self.explanation_field_combo.currentText()
        CONFIG["explanation_audio_field"] = self.explanation_audio_field_combo.currentText()
        CONFIG["api_key"] = self.api_key_input.text()
        CONFIG["gpt_prompt"] = self.gpt_prompt_input.text()
        
        # Save to disk
        save_config()
        self.accept()

# Process a single note with debug mode
def process_note_debug(note, override_existing=True, progress_callback=None):
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
        if not CONFIG["api_key"]:
            debug_write("No API key set")
            return False, "No OpenAI API key set. Please set your API key in the settings."

        # Extract data from note
        debug_write("Extracting data from note")
        word = note[CONFIG["word_field"]] if CONFIG["word_field"] in note else ""
        sentence = note[CONFIG["sentence_field"]] if CONFIG["sentence_field"] in note else ""
        definition = note[CONFIG["definition_field"]] if CONFIG["definition_field"] in note else ""
        picture = note[CONFIG["picture_field"]] if CONFIG["picture_field"] in note else ""
        
        debug_write(f"Word field: {CONFIG['word_field']} = {word[:30]}...")
        debug_write(f"Sentence field: {CONFIG['sentence_field']} = {sentence[:30]}...")
        debug_write(f"Definition field: {CONFIG['definition_field']} = {definition[:30]}...")
        debug_write(f"Picture field: {CONFIG['picture_field']} = {'Has content' if picture else 'Empty'}")
        
        # Check if explanation already exists and we're not overriding
        if not override_existing:
            debug_write("Checking if content already exists")
            explanation_exists = CONFIG["explanation_field"] in note and note[CONFIG["explanation_field"]].strip()
            audio_exists = CONFIG["explanation_audio_field"] in note and note[CONFIG["explanation_audio_field"]].strip()
            
            debug_write(f"Explanation exists: {explanation_exists}")
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
                
            explanation = process_with_openai(CONFIG["api_key"], prompt, picture)
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
            if override_existing or not note[CONFIG["explanation_field"]].strip():
                try:
                    note[CONFIG["explanation_field"]] = explanation
                    debug_write("Explanation saved to note")
                    
                    if progress_callback:
                        progress_callback("Explanation saved to note")
                except Exception as e:
                    debug_write(f"Error setting explanation field: {str(e)}")
                    log_error(f"Error setting explanation field: {CONFIG['explanation_field']}", e)
                    return False, f"Error saving explanation to note: {str(e)}"
        
        # Generate audio with VOICEVOX if available
        if CONFIG["explanation_audio_field"] in note:
            if check_voicevox_running():
                debug_write(f"Processing audio for field: {CONFIG['explanation_audio_field']}")
                if override_existing or not note[CONFIG["explanation_audio_field"]].strip():
                    try:
                        debug_write("Calling generate_audio")
                        
                        if progress_callback:
                            progress_callback("Generating audio with VOICEVOX...")
                            
                        audio_path = generate_audio(CONFIG["api_key"], explanation)
                        
                        if audio_path:
                            # Get just the filename from the path
                            audio_filename = os.path.basename(audio_path)
                            debug_write(f"Audio generation returned: {audio_path}")
                            debug_write(f"Audio file exists, basename: {audio_filename}")
                            
                            # Save the audio reference to the note
                            debug_write("Saving audio reference to note")
                            note[CONFIG["explanation_audio_field"]] = f"[sound:{audio_filename}]"
                            debug_write("Audio reference saved to note")
                            
                            if progress_callback:
                                progress_callback("Audio generated and saved to note")
                        else:
                            debug_write("Audio generation failed, setting placeholder text")
                            note[CONFIG["explanation_audio_field"]] = "[Audio generation failed]"
                            
                            if progress_callback:
                                progress_callback("Audio generation failed")
                    except Exception as e:
                        debug_write(f"Error in audio generation: {str(e)}")
                        log_error("Error in audio generation", e)
                        # Continue even if audio generation fails
                        
                        if progress_callback:
                            progress_callback(f"Error generating audio: {str(e)}")
            else:
                debug_write("VOICEVOX is not running, setting placeholder text")
                if override_existing or not note[CONFIG["explanation_audio_field"]].strip():
                    try:
                        note[CONFIG["explanation_audio_field"]] = "[VOICEVOX not running - please start VOICEVOX to generate audio]"
                        debug_write("Added placeholder text to audio field")
                        
                        if progress_callback:
                            progress_callback("VOICEVOX not running - skipped audio generation")
                    except Exception as e:
                        debug_write(f"Error setting audio field: {str(e)}")
                        # Continue even if this fails
        
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
        progress.setWindowTitle("GPT Explanation Generator")
        progress.setMinimumDuration(0)  # Show immediately
        progress.setAutoClose(False)    # Don't close automatically
        progress.setAutoReset(False)    # Don't reset automatically
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)  # Block input to other windows
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
        
        # Ask for confirmation if content exists
        override_existing = True
        if explanation_exists or audio_exists:
            progress.cancel()  # Hide progress dialog during confirmation
            
            msg = "This card already has "
            if explanation_exists and audio_exists:
                msg += "an explanation and audio."
            elif explanation_exists:
                msg += "an explanation."
            else:
                msg += "explanation audio."
            
            msg += " Do you want to override it?"
            
            if not askUser(msg, title="Override Existing Content?"):
                tooltip("Operation cancelled.")
                return
                
            # Re-create progress dialog after confirmation
            progress = QProgressDialog("Processing...", "Cancel", 0, 100, mw)
            progress.setWindowTitle("GPT Explanation Generator")
            progress.setMinimumDuration(0)
            progress.setAutoClose(False)
            progress.setAutoReset(False)
            progress.setWindowModality(Qt.WindowModality.ApplicationModal)
            progress.setValue(20)
            progress.setLabelText("Checking VOICEVOX status...")
            progress.show()
            QApplication.processEvents()
        
        progress.setValue(30)
        progress.setLabelText("Checking VOICEVOX status...")
        QApplication.processEvents()
        
        # Check if VOICEVOX is running if audio field is configured
        if CONFIG["explanation_audio_field"] and not check_voicevox_running():
            progress.cancel()  # Hide progress dialog during confirmation
            
            if askUser("VOICEVOX is not running. Audio generation will be skipped. Do you want to continue without audio?", title="VOICEVOX Not Running"):
                # Re-create progress dialog after confirmation
                progress = QProgressDialog("Processing...", "Cancel", 0, 100, mw)
                progress.setWindowTitle("GPT Explanation Generator")
                progress.setMinimumDuration(0)
                progress.setAutoClose(False)
                progress.setAutoReset(False)
                progress.setWindowModality(Qt.WindowModality.ApplicationModal)
                progress.setValue(30)
                progress.setLabelText("Generating explanation with OpenAI...")
                progress.show()
                QApplication.processEvents()
            else:
                tooltip("Operation cancelled. Please start VOICEVOX and try again.")
                return
        
        progress.setValue(40)
        progress.setLabelText("Generating explanation with OpenAI...")
        QApplication.processEvents()
        
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
                    elif "Generating audio" in message:
                        progress_value = 80
                    elif "Audio generated" in message:
                        progress_value = 90
                    elif "Saving changes" in message:
                        progress_value = 95
                    elif "Changes saved successfully" in message:
                        progress_value = 98
                    
                    mw.taskman.run_on_main(lambda: update_progress_ui(message, progress_value))
                
                def update_progress_ui(message, value):
                    progress.setValue(value)
                    progress.setLabelText(message)
                    QApplication.processEvents()
                
                # Call process_note with the progress callback
                result, message = process_note(note, override_existing, update_progress)
                
                # Update UI on the main thread
                mw.taskman.run_on_main(lambda: handle_process_result(result, message, card, progress))
            except Exception as e:
                error_msg = str(e)
                log_error("Error in process_with_progress", e)
                mw.taskman.run_on_main(lambda: show_error(error_msg, progress))
        
        # Function to handle the result on the main thread
        def handle_process_result(success, message, card, progress):
            if success:
                progress.setValue(100)
                progress.setLabelText("Refreshing card...")
                QApplication.processEvents()
                try:
                    card.load()  # Refresh the card to show new content
                    progress.cancel()
                    tooltip("Explanation generated successfully!")
                except Exception as e:
                    log_error("Error in card.load()", e)
                    progress.cancel()
                    tooltip("Explanation generated, but failed to refresh card.")
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
        
        # Function to show error on the main thread
        def show_error(error_msg, progress):
            progress.cancel()
            error_dialog = QMessageBox(mw)
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("Error")
            error_dialog.setText("Failed to generate explanation")
            error_dialog.setInformativeText(f"Error: {error_msg}")
            error_dialog.setDetailedText(f"Please check the error log for more details.\n\nError: {error_msg}")
            error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
            error_dialog.exec()
        
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
            
            button.innerText = 'Generate Explanation';
            
            // Set up the click handler with debugging
            button.onclick = function() {
                console.log('Generate Explanation button clicked');
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
            
            console.log('GPT Explanation button added successfully');
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
    action = QAction("GPT Explanation Settings", mw)
    qconnect(action.triggered, open_settings)
    mw.form.menuTools.addAction(action)
    
    # Remove browser menu action for bulk processing
    # gui_hooks.browser_menus_did_init.append(setup_browser_menu)

# Open settings dialog
def open_settings():
    dialog = ConfigDialog(mw)
    dialog.exec()

# Initialize the add-on
def init():
    try:
        log_error("Initializing GPT Explanation addon")
        
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
        
        log_error("GPT Explanation addon initialization complete")
    except Exception as e:
        log_error(f"Error during initialization: {str(e)}")
        log_error(traceback.format_exc())

# Run initialization
init()