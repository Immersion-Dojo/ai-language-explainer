# AI Language Explainer for Anki

> **Generate AI-powered explanations for language learning with high-quality text-to-speech audio**

This Anki add-on helps language learners understand vocabulary words in context by generating explanations using OpenAI's GPT-4.1 AND relevant audio for those definitions.

## ✨ Features

### 🧠 **Intelligent Explanations**
- Automatically generates contextual explanations for words based on definition, example sentence, and usage.
- Uses OpenAI's latest GPT-4.1 model for accurate, beginner-friendly explanations
- Customizable prompts to match your learning style and level

### 🎵 **High-Quality Audio Generation**
- **Multiple TTS Engines**: Choose from VoiceVox, AivisSpeech, ElevenLabs, or OpenAI TTS
- **Voice Preview & Selection**: Listen to samples and choose your preferred voice for AivisSpeech and VoiceVox
- **Batch Processing**: Generate audio for multiple cards at once

### ⚙️ **Flexible Configuration**
- Works with any note type (fully configurable fields)
- Tabbed settings interface for easy organization
- Option to disable audio generation or hide UI elements
- Separate override controls for text and audio regeneration

### 🚀 **User Experience**
- One-click generation during card review
- Batch processing from the browser
- Progress tracking with detailed status updates
- Comprehensive error handling and logging

## 📥 Installation

1. **Install the add-on** through Anki's add-on manager
2. **Configure settings** by going to `Tools > AI Language Explainer > Settings`
3. **Set up your note type** and field mappings
4. **Add your OpenAI API key**
5. **Choose your preferred TTS engine** (optional)

## ⚡ Quick Setup

### 1. Basic Configuration
- **Note Type**: Select your card type (e.g., "Sentence Mining", "Vocabulary")
- **Input Fields**: Map your word, sentence, and definition fields
- **Output Fields**: Set where explanations and audio should be saved
- **OpenAI API Key**: Enter your API key for text generation

### 2. Audio Setup (Optional)

#### **VoiceVox** (Free, Japanese-focused)
1. Download and install [VOICEVOX](https://voicevox.hiroshiba.jp/)
2. Start VOICEVOX before using the add-on (runs on `http://localhost:50021`)
3. Test connection and select preferred voice in settings

#### **AivisSpeech** (Free, High-quality)
1. Download and install [AivisSpeech Engine](https://aivis.dev/)
2. Start the engine (runs on `http://127.0.0.1:10101`)
3. Load voices and select default in the add-on settings
4. Download additional voices from [AivisHub](https://aivis.dev/hub)

#### **ElevenLabs** (Premium, Multilingual)
1. Create an account at [ElevenLabs](https://elevenlabs.io/)
2. Get your API key and voice ID
3. Enter credentials in the TTS settings

#### **OpenAI TTS** (Premium, Reliable)
1. Use the same OpenAI API key as text generation
2. Choose from available voices (alloy, echo, fable, etc.)

## 🎯 Usage

### During Review
1. Review your card as normal
2. Click **"Generate explanation"** button when answer is shown
3. Choose whether to override existing content
4. Wait for AI generation and audio synthesis
5. New content appears automatically on your card

### Batch Processing
1. Open the Anki browser
2. Select cards you want to process
3. Go to `Edit > Batch Generate AI Explanations`
4. Choose override options
5. Monitor progress and review results

## 🛠️ Requirements

- **Anki**: Version 2.1.50+ (tested with Anki 25+)
- **OpenAI API Key**: With GPT-4.1 access and sufficient credits
- **Internet Connection**: For API calls
- **TTS Engine** (optional): Choose from supported engines for audio generation

## 🔧 Troubleshooting

### Common Issues

**API Key Problems**
- Verify your OpenAI API key is valid and has sufficient credits
- Use the "Validate Key" button in settings to test connectivity

**Field Configuration**
- Ensure all configured fields exist in your note type
- Check field names match exactly (case-sensitive)

**Audio Generation**
- **VoiceVox**: Ensure application is running and API server is enabled
- **AivisSpeech**: Check engine is running on port 10101
- **ElevenLabs**: Verify API key and voice ID are correct
- **OpenAI TTS**: Confirm API key has TTS access

**Performance Issues**
- Check your internet connection stability
- Monitor API rate limits and usage quotas
- Review debug logs in the add-on directory

### Debug Information
Check these files in your add-on directory for detailed error information:
- `debug_log.txt` - General operation logs
- `crash_log.txt` - System crash information
- `process_debug.txt` - Note processing details

## 🌟 Advanced Features

### Custom Prompts
Modify the GPT prompt to match your learning style:
- Adjust explanation complexity
- Change target language focus
- Customize example formats

### Voice Management
- Preview all available voices before selecting
- Set different defaults for different contexts
- Sample generation with custom text

### Batch Operations
- Process entire deck sections at once
- Skip cards that already have content
- Separate text and audio override controls

## 🎓 Learning Resources

**Want to learn more about effective language learning?**

Check out [Matt vs Japan's Immersion Dojo](https://www.skool.com/mattvsjapan/about?ref=837f80b041cf40e9a3979cd1561a67b2) for advanced language learning theory and community support.

## 📝 License

This project is open source. See the repository for license details.

## 🤝 Contributing

Found a bug or have a feature request? Please open an issue on the GitHub repository.

---

*Happy language learning! 🌍📚* 
