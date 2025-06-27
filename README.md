# Text Creator

A desktop application that allows you to transcribe speech to text using OpenAI's Whisper API and insert it into the currently focused text field using a customizable hotkey.

## Features

- Global hotkey (configurable) to start/stop recording
- System tray integration for easy access
- Configurable settings (hotkey)
- Uses OpenAI's Whisper API for high-quality transcription
- English language speech recognition
- Low latency recording and transcription
- Visual recording indicator
- Standalone executable option via PyInstaller

## Requirements

- Python 3.8+ (development)
- FFmpeg (required for audio processing)
- A working microphone
- OpenAI API key with access to the Whisper API
- Dependencies:
  - PyQt6
  - sounddevice
  - numpy
  - openai
  - soundfile
  - keyboard
  - pyinstaller (for building)

## Installation

### Development Setup

1. Clone this repository:
   ```
   git clone https://github.com/your-username/text-creator.git
   cd text-creator
   ```

2. (Optional) Create a virtual environment:
   This step is optional but can help avoid package conflicts with other Python projects.
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install the required dependencies using the included requirements.txt file:
   ```
   pip install -r requirements.txt
   ```
   
   This will install all necessary packages: PyQt6, sounddevice, numpy, openai, soundfile, and keyboard.

4. Install FFmpeg:
   - On Windows: Download from https://ffmpeg.org/download.html and add to PATH
   - On macOS: `brew install ffmpeg`
   - On Ubuntu/Debian: `sudo apt install ffmpeg`

5. Get an OpenAI API key from https://platform.openai.com/api-keys

### Building the Executable

To build a standalone executable:

1. Install PyInstaller:
   ```
   pip install pyinstaller
   ```

2. Run the build script:
   ```
   # On Windows
   build.bat
   
   # On macOS/Linux
   # Run PyInstaller directly or create an equivalent shell script
   pyinstaller --noconfirm --clean --windowed --onefile --name "TextCreator" text_creator.py
   ```

3. The executable will be created in the `dist` folder

## Usage

### Running from Source

1. Run the application:
   ```
   python text_creator.py
   ```
   
2. The application will start in the system tray (look for the icon in the taskbar)

3. Right-click the system tray icon and select "Settings"

4. Enter your OpenAI API key and configure your preferred settings

5. Press the configured hotkey to start recording

6. Speak clearly into your microphone

7. Press the hotkey again to stop recording and the transcribed text will be inserted at the current cursor position

### Running the Executable

1. Double-click the TextCreator executable in the dist folder

2. Configure your settings on first run

3. Use the hotkey to start/stop recording

## Configuration

Click on the system tray icon and select "Settings" to configure:

- **OpenAI API Key** (required): Your personal API key for accessing OpenAI's services
- **Hotkey**: The keyboard combination to start/stop recording (default: ctrl+alt+d)

### Hotkey Format

When setting a custom hotkey, use the following format:

- Use key names separated by `+` signs (e.g., `ctrl+alt+d`)  
- Supported modifier keys: `ctrl`, `alt`, `shift`
- Examples:
  - `ctrl+alt+d` (Control + Alt + D)
  - `ctrl+shift+x` (Control + Shift + X)
  - `alt+f` (Alt + F)
  - `f9` (F9 key alone)

Configuration is stored in `text_creator_sensitive.json` located in the application directory. This file contains your API key and hotkey settings.

## Git Integration

### Setting Up for Version Control

1. Initialize Git repository (if not already done):
   ```
   git init
   ```

2. Create a `.gitignore` file to exclude sensitive and build files:
   ```
   # API Keys and sensitive data
   text_creator_sensitive.json
   
   # Python
   __pycache__/
   *.py[cod]
   *$py.class
   *.so
   .Python
   env/
   build/
   develop-eggs/
   dist/
   downloads/
   eggs/
   .eggs/
   lib/
   lib64/
   parts/
   sdist/
   var/
   *.egg-info/
   .installed.cfg
   *.egg
   
   # Virtual Environment
   venv/
   ENV/
   
   # IDE specific files
   .idea/
   .vscode/
   *.swp
   *.swo
   ```

3. Add files to the repository:
   ```
   git add .
   git commit -m "Initial commit"
   ```

4. Add a remote repository (if you've created one):
   ```
   git remote add origin https://github.com/your-username/text-creator.git
   git branch -M main
   git push -u origin main
   ```

## Contributing

Contributions are welcome! Here are some ways you can contribute:

1. Report bugs and issues
2. Suggest new features
3. Submit pull requests with improvements
4. Help with documentation

Please follow these steps for contributions:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Troubleshooting

- If you get an error about the audio device, make sure your microphone is properly connected and selected as the default recording device
- For better accuracy, speak clearly and minimize background noise
- If you get API authentication errors, double-check your OpenAI API key in the settings
- If the application crashes on startup, try running it from a terminal to see the error message
- For PyInstaller issues, check that all dependencies are properly included

## Notes

- The application requires an active internet connection to use the Whisper API
- Audio is sent to OpenAI's servers for processing - ensure you're comfortable with this if handling sensitive information
- You can monitor your API usage at https://platform.openai.com/usage
- The Whisper API is billed separately from other OpenAI services

## License

MIT
