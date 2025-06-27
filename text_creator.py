import sys
import os
import json
import tempfile
import threading
import time
import keyboard
import sounddevice as sd
import numpy as np
from openai import OpenAI
from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QMessageBox,
                           QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QStyle,
                           QHBoxLayout, QTextEdit)
from PyQt6.QtGui import QIcon, QAction, QColor, QPainter, QPen, QFont
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer, QPoint, QRect, QPropertyAnimation

# Determine if running as bundled exe
def get_application_path():
    """Get the path to the application - works for dev and for PyInstaller"""
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the PyInstaller bootloader
        # extends the sys module by a flag frozen=True and sets the app 
        # path into variable _MEIPASS
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    return application_path

# Main config file (stored in user's home directory)
MAIN_CONFIG_FILE = os.path.expanduser('~/.text_creator_config.json')

# Sensitive config file (stored next to the executable in bundled mode, or in program directory in dev mode)
SENSITIVE_CONFIG_FILE = os.path.join(get_application_path(), 'text_creator_sensitive.json')

# Default configurations
DEFAULT_MAIN_CONFIG = {
    'model': 'whisper-1',  # OpenAI's Whisper API model
    'language': 'en',
    'energy_threshold': 500,
    'record_timeout': 2.0,
    'phrase_timeout': 3.0
}

DEFAULT_SENSITIVE_CONFIG = {
    'hotkey': '',  # Will be prompted if not found in config
    'api_key': ''  # Will be prompted if not found in config
}

class RecordingIndicator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Set window size and position at bottom center
        screen_rect = QApplication.primaryScreen().availableGeometry()
        self.setFixedSize(300, 40)
        self.move(
            (screen_rect.width() - self.width()) // 2,
            screen_rect.height() - 60
        )
        
        # Create a label for the recording indicator
        self.label = QLabel("Listening...")
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
                background-color: rgba(220, 53, 69, 0.8);
                border-radius: 10px;
                padding: 8px 16px;
            }
        """)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        # Add pulsing animation
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(1000)
        self.animation.setStartValue(0.6)
        self.animation.setKeyValueAt(0.5, 1.0)
        self.animation.setEndValue(0.6)
        self.animation.setLoopCount(-1)  # Infinite loop
        
    def show(self):
        super().show()
        self.animation.start()
        
    def hide(self):
        self.animation.stop()
        super().hide()


class AudioRecorder(QObject):
    recording_finished = pyqtSignal(str)
    status_update = pyqtSignal(str)  # Signal for status updates
    recording_state_changed = pyqtSignal(bool)  # New signal for recording state changes
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.is_recording = False
        self.audio_data = []
        self.sample_rate = 16000
        self.recording_thread = None
        self.client = None
        self.recording_indicator = RecordingIndicator()
        self.recording_state_changed.connect(self._update_recording_indicator)
        
        # Initialize the OpenAI client
        self._init_openai_client()
    
    def _init_openai_client(self):
        """Initialize the OpenAI client with the API key from config"""
        try:
            api_key = self.config.get('api_key')
            if not api_key or not api_key.strip() or 'your-api-key' in api_key:
                error_msg = "Error: No valid OpenAI API key found in config"
                print(error_msg)
                self.status_update.emit(error_msg)
                return False
                
            print("Initializing OpenAI client...")
            self.client = OpenAI(api_key=api_key)
            
            # Test the client with a simple API call
            try:
                # This is just a lightweight test to verify the API key
                self.client.models.list()
                print("OpenAI client initialized successfully")
                return True
            except Exception as e:
                error_msg = f"Error testing OpenAI API: {str(e)}"
                print(error_msg)
                self.status_update.emit(error_msg)
                self.client = None
                return False
                
        except Exception as e:
            error_msg = f"Error initializing OpenAI client: {str(e)}"
            print(error_msg)
            self.status_update.emit(error_msg)
            self.client = None
            return False
    
    def _update_recording_indicator(self, is_recording):
        if is_recording:
            self.recording_indicator.show()
        else:
            self.recording_indicator.hide()
    
    def update_config(self, new_config):
        """Update configuration and reinitialize the OpenAI client"""
        self.config = new_config
        
        # Stop recording if active
        was_recording = False
        if self.is_recording:
            was_recording = True
            self.stop_recording()
            
        # Reinitialize the OpenAI client with the new API key
        success = self._init_openai_client()
        
        # Provide feedback based on initialization result
        if success:
            self.status_update.emit("API key updated successfully")
        else:
            self.status_update.emit("Error: Failed to initialize with new API key")
        
        return success
    def _show_api_key_settings(self):
        """Show settings dialog to update API key"""
        print("Opening settings to update API key...")
        # This will be handled by the main application's show_settings method
        # We'll use QApplication.instance() to access the main app
        app = QApplication.instance()
        if hasattr(app, 'show_settings'):
            app.show_settings()
        else:
            print("Warning: Could not access application settings")
        
    def start_recording(self):
        try:
            print("\n--- Starting recording ---")
            print(f"Current recording state: {self.is_recording}")
            
            if self.is_recording:
                print("Already recording!")
                return False
                
            # Ensure we have a valid OpenAI client
            if not self.client and not self._init_openai_client():
                error_msg = "Error: Failed to initialize OpenAI client. Please check your API key."
                print(error_msg)
                self.status_update.emit(error_msg)
                
                # Try to open settings to let user update the API key
                QTimer.singleShot(1000, self._show_api_key_settings)
                return False
            
            # List available audio devices
            print("\nAvailable audio devices:")
            devices = sd.query_devices()
            for i, device in enumerate(devices):
                print(f"{i}: {device['name']} (Input channels: {device['max_input_channels']})")
            
            # Get default input device
            default_input = sd.default.device[0]
            print(f"\nUsing default input device: {default_input} - {devices[default_input]['name']}")
            
            self.is_recording = True
            self.audio_data = []
            self.status_update.emit("Recording...")
            self.recording_state_changed.emit(True)
            
            # Start recording in a separate thread
            self.recording_thread = threading.Thread(target=self._record_audio)
            self.recording_thread.daemon = True  # Make thread exit when main program exits
            self.recording_thread.start()
            
            print("Recording started successfully")
            return True
            
        except Exception as e:
            error_msg = f"Error in start_recording: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            self.status_update.emit(error_msg)
            self.is_recording = False
            self.recording_state_changed.emit(False)
            return False
    
    def stop_recording(self):
        if not self.is_recording:
            return ""
            
        self.is_recording = False
        self.recording_state_changed.emit(False)  # Emit signal that recording stopped
        if self.recording_thread:
            self.recording_thread.join()
        
        if not self.audio_data:
            self.status_update.emit("No audio recorded")
            return ""
            
        # Save audio to a temporary file
        audio_np = np.concatenate(self.audio_data, axis=0)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            import soundfile as sf
            sf.write(f.name, audio_np, self.sample_rate)
            
            try:
                self.status_update.emit("Transcribing...")
                # Transcribe using Whisper API
                with open(f.name, 'rb') as audio_file:
                    response = self.client.audio.transcriptions.create(
                        model=self.config['model'],
                        file=audio_file,
                        language=self.config['language']
                    )
                text = response.text.strip()
                if text:
                    self.status_update.emit("Transcription complete")
                return text
            except Exception as e:
                error_msg = f"Error in transcription: {str(e)}"
                self.status_update.emit(error_msg)
                print(error_msg)
                return ""
            finally:
                try:
                    os.unlink(f.name)
                except:
                    pass
    
    def _record_audio(self, channels=1):
        print(f"\n--- Starting audio capture (channels: {channels}, sample rate: {self.sample_rate}) ---")
        
        def audio_callback(indata, frames, time, status):
            try:
                if status:
                    print(f"Audio status: {status}")
                if self.is_recording:
                    self.audio_data.append(indata.copy())
                    # Print a dot every 50 chunks to show recording is active
                    if len(self.audio_data) % 50 == 0:
                        print('.', end='', flush=True)
            except Exception as e:
                print(f"Error in audio callback: {e}")
        
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=channels,
                callback=audio_callback,
                dtype='float32',
                device=sd.default.device[0],  # Explicitly use default input device
                blocksize=1024  # Standard block size
            ):
                print("Audio stream opened successfully")
                print("Recording... (press hotkey again to stop)")
                
                # Keep the stream alive while recording
                while self.is_recording:
                    sd.sleep(100)
                    
        except Exception as e:
            error_msg = f"Error in audio stream: {str(e)}"
            print(f"\n{error_msg}")
            self.status_update.emit(error_msg)
            import traceback
            traceback.print_exc()
            self.is_recording = False
            self.recording_state_changed.emit(False)
        
        print("\nAudio capture ended")

class TextCreatorApp(QApplication):
    def __init__(self, sys_argv):
        super().__init__(sys_argv)
        self.setQuitOnLastWindowClosed(False)
        
        # Load or create config
        self.config = self._load_config()
        
        # Setup system tray first so it can be used for notifications
        self.setup_system_tray()
        
        # Initialize audio recorder
        self.recorder = AudioRecorder(self.config)
        self.recorder.status_update.connect(self.update_status)
        
        # Check for required configuration and prompt if needed
        self._check_required_config()
        
        # Register hotkey
        self.register_hotkey()
        
    def _check_required_config(self):
        """Check for required sensitive configuration and prompt user if needed"""
        # Check if API key and hotkey are set
        needs_config = False
        
        if not self.config.get('api_key'):
            print("API key not found in configuration")
            needs_config = True
            
        if not self.config.get('hotkey'):
            print("Hotkey not found in configuration")
            needs_config = True
            
        # If any required config is missing, open the settings dialog
        if needs_config:
            print("Opening settings dialog to prompt for required configuration...")
            self._open_settings()
        
    def _load_config(self):
        # Load main config
        main_config = DEFAULT_MAIN_CONFIG.copy()
        if os.path.exists(MAIN_CONFIG_FILE):
            try:
                with open(MAIN_CONFIG_FILE, 'r') as f:
                    main_config.update(json.load(f))
            except Exception as e:
                print(f"Error loading main config: {e}")
        
        # Load sensitive config
        sensitive_config = DEFAULT_SENSITIVE_CONFIG.copy()
        if os.path.exists(SENSITIVE_CONFIG_FILE):
            try:
                with open(SENSITIVE_CONFIG_FILE, 'r') as f:
                    sensitive_config.update(json.load(f))
            except Exception as e:
                print(f"Error loading sensitive config: {e}")
        
        # Combine configs, with sensitive config taking precedence
        combined_config = {**main_config, **sensitive_config}
        return combined_config
    
    def _save_config(self):
        # Split config into main and sensitive parts
        main_config = {}
        sensitive_config = {}
        
        # Extract sensitive settings
        for key, value in self.config.items():
            if key in DEFAULT_SENSITIVE_CONFIG:
                sensitive_config[key] = value
            else:
                main_config[key] = value
        
        # Save main config
        try:
            with open(MAIN_CONFIG_FILE, 'w') as f:
                json.dump(main_config, f, indent=4)
        except Exception as e:
            print(f"Error saving main config: {e}")
        
        # Save sensitive config
        try:
            with open(SENSITIVE_CONFIG_FILE, 'w') as f:
                json.dump(sensitive_config, f, indent=4)
        except Exception as e:
            print(f"Error saving sensitive config: {e}")
            
    def update_config(self, new_config):
        """Update config with new values and save"""
        self.config.update(new_config)
        self._save_config()
        
        # If hotkey changed, re-register it
        if 'hotkey' in new_config:
            self.register_hotkey()
    
    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(self.style().standardIcon(
            getattr(QStyle.StandardPixmap, 'SP_ComputerIcon'))))
        
        menu = QMenu()
        
        # Settings action
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        menu.addAction(settings_action)
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.quit_application)
        menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()
    
    def register_hotkey(self):
        try:
            print("Unregistering any existing hotkeys...")
            keyboard.unhook_all()
            
            # Get the hotkey from config, with a default if not found
            hotkey_combination = self.config.get('hotkey')
            if not hotkey_combination:
                # Fallback to default hotkey if none is set
                hotkey_combination = 'ctrl+alt+d'
                self.config['hotkey'] = hotkey_combination
                self._save_config()  # Save the default hotkey to config
                
            print(f"Registering new hotkey: {hotkey_combination}")
            
            # Register the hotkey with suppress=False to avoid eating the keypress
            keyboard.add_hotkey(
                hotkey_combination,
                self.toggle_recording,
                suppress=False,  # Changed from True to False
                trigger_on_release=False
            )
            
            print("Hotkey registration completed")
            print(f"Press {hotkey_combination} to start/stop recording")
            
        except Exception as e:
            print(f"Error in register_hotkey: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_recording(self, *args):
        print("\n--- Hotkey pressed! ---")
        try:
            # Ensure the recording state is properly initialized
            if not hasattr(self, 'is_recording'):
                self.is_recording = False
            
            print(f"Current recording state before toggle: {self.is_recording}")
            
            # Toggle the recording state
            if self.is_recording:
                print("Stopping recording...")
                self.is_recording = False
                try:
                    text = self.recorder.stop_recording()
                    if text and text.strip():
                        print(f"Transcription successful. Text length: {len(text)} characters")
                        keyboard.write(text)
                    else:
                        print("No text was transcribed")
                except Exception as e:
                    print(f"Error during stop_recording: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("Starting recording...")
                try:
                    if self.recorder.start_recording():
                        self.is_recording = True
                        print("Recording started successfully")
                    else:
                        print("Failed to start recording - check audio device and permissions")
                except Exception as e:
                    print(f"Error during start_recording: {e}")
                    import traceback
                    traceback.print_exc()
                    
            print(f"New recording state: {self.is_recording}")
            
        except Exception as e:
            print(f"Unexpected error in toggle_recording: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("--- Hotkey handling complete ---\n")
    
    def _open_settings(self):
        """Open settings dialog and wait for user input"""
        # Create and show settings dialog
        self.settings_window = SettingsWindow(self.config, self)
        self.settings_window.setWindowModality(Qt.WindowModality.ApplicationModal)  # Make it modal so user must interact
        self.settings_window.show()
        # This will show a message in the tray to guide the user
        self.update_status("Please enter your API key and hotkey in the settings dialog")
        
    def show_settings(self):
        """Show settings dialog when user requests it"""
        self._open_settings()
        self.settings_window.raise_()
        self.settings_window.activateWindow()
    
    def update_config(self, new_config):
        self.config = new_config
        self._save_config()
        self.register_hotkey()
        
        # Update the recorder with the new API key
        self.recorder.update_config(self.config)
    
    def update_status(self, message):
        """Update the status in the system tray"""
        self.tray_icon.showMessage("Text Creator", message)
    
    def quit_application(self):
        self.recorder.stop_recording()
        self.quit()

class SettingsWindow(QWidget):
    def __init__(self, config, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.config = config.copy()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('Text Creator Settings')
        self.setGeometry(300, 300, 400, 400)
        
        layout = QVBoxLayout()
        
        # API Key setting
        api_key_layout = QVBoxLayout()
        api_key_layout.addWidget(QLabel('OpenAI API Key:'))
        self.api_key_edit = QTextEdit()  # Changed to QTextEdit for multi-line and clear text
        self.api_key_edit.setFixedHeight(100)  # Increased height to fit the API key better
        if self.config.get('api_key'):
            self.api_key_edit.setText(self.config['api_key'])  # Show the actual key
        api_key_layout.addWidget(self.api_key_edit)
        
        # Hotkey setting
        hotkey_layout = QVBoxLayout()
        hotkey_layout.addWidget(QLabel('Hotkey:'))
        self.hotkey_edit = QLineEdit(self.config['hotkey'])
        hotkey_layout.addWidget(self.hotkey_edit)
        
        # Add hotkey format help text
        hotkey_help = QLabel(
            "Format: Use key names separated by '+' signs (e.g., 'ctrl+alt+d')\n" 
            "Examples: 'ctrl+shift+x', 'alt+f', 'f9'"
        )
        hotkey_help.setStyleSheet("color: gray; font-size: 10px;")
        hotkey_layout.addWidget(hotkey_help)
        
        # Language is fixed to English, so no input field is needed
        
        # Save button
        save_btn = QPushButton('Save Settings')
        save_btn.clicked.connect(self.save_settings)
        
        layout.addLayout(api_key_layout)
        layout.addLayout(hotkey_layout)
        layout.addStretch()
        layout.addWidget(save_btn)
        
        self.setLayout(layout)
    
    def save_settings(self):
        new_config = {
            'hotkey': self.hotkey_edit.text(),
            'language': 'en',  # Language is fixed to English
            'api_key': self.api_key_edit.toPlainText().strip()  # Get text from QTextEdit
        }
        
        # Test the API key validity before saving
        api_key = new_config.get('api_key')
        if not api_key or api_key.strip() == '' or api_key.lower() == 'your-api-key-here':
            # Show a warning if the API key is empty or default
            QMessageBox.warning(self, 'Warning', 'No API key provided. The application may not work correctly.')
            # Still save the settings and close
            self.config.update(new_config)
            self.parent_app.update_config(self.config)
            self.close()
            return
        
        # Validate the API key with OpenAI
        try:
            # Create a temporary client to test the key
            client = OpenAI(api_key=api_key)
            # Make a lightweight API call to verify the key
            client.models.list()
            
            # Key is valid, update configuration and close
            self.config.update(new_config)
            self.parent_app.update_config(self.config)
            self.close()
            
        except Exception as e:
            # Extract error message
            error_msg = str(e)
            if 'invalid_api_key' in error_msg or '401' in error_msg:
                # Show a specific message for invalid API key
                QMessageBox.warning(self, 'Invalid API Key', 
                                  f'The API key you entered appears to be invalid. OpenAI error:\n{error_msg}')
            else:
                # Show other errors
                QMessageBox.warning(self, 'API Error', 
                                  f'Error validating API key with OpenAI:\n{error_msg}')
            
            # Let user decide whether to save anyway
            response = QMessageBox.question(self, 'Save Anyway?', 
                                        'Do you want to save this key anyway and close the settings?',
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if response == QMessageBox.StandardButton.Yes:
                # Save and close despite the error
                self.config.update(new_config)
                self.parent_app.update_config(self.config)
                self.close()

def main():
    app = TextCreatorApp(sys.argv)
    sys.exit(app.exec())

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
