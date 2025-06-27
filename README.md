# AI Language Explainer for Anki

> **Generate AI-powered explanations for language learning with high-quality text-to-speech audio**

This Anki add-on helps language learners understand vocabulary words in context by generating explanations of target words using OpenAI's models AND relevant audio.

## ✨ Features

### 🧠 **Intelligent Explanations**
- Automatically generates contextual explanations for target words based on a definition (optional), example sentence, and usage.
- Choose any OpenAI text model (eg, GPT-4.1, GPT-4o, GPT-3.5) for accurate, beginner-friendly explanations
- Customizable prompts to match your learning style and level

### 🎵 **High-Quality Audio Generation**
- **Multiple TTS Engines**: Choose from VoiceVox, AivisSpeech, ElevenLabs, or OpenAI TTS
- **Voice Preview & Selection**: Listen to samples and choose your preferred voice for AivisSpeech and VoiceVox
- **Adjustable Speed**: Adjust the speed of OpenAI TTS with a slider
- **Batch Processing**: Generate audio for multiple cards at once

### ⚙️ **Flexible Configuration**
- Works with any note type (fully configurable fields)
- Tabbed settings interface for easy organization
- Option to disable text generation or audio generation or
- Hide UI elements

### 🚀 **User Experience**
- One-click generation during card review
- Batch processing from the browser
- Comprehensive error handling and logging

## 📥 Installation

1. **Install the add-on** through Anki's add-on manager
2. **Configure settings** by going to `Tools > AI Language Explainer > Settings`
3. **Set up your note type** and field mappings
4. **Add your OpenAI API key** under the `Text Generation` tab
5. **Choose your preferred TTS engine** (optional)

## ⚡ Quick Setup

### 1. Basic Configuration
- **Note Type**: Select your card type (e.g., "Sentence Mining", "Vocabulary")
- **Input Fields**: Map your target word, sentence, and definition fields
- **Output Fields**: Set where explanations and audio should be saved
- **OpenAI API Key**: Enter your API key for text generation

### 2. Audio Setup (Optional)

#### **VoiceVox** (Free, Japanese-focused)
1. Download and install [VOICEVOX](https://voicevox.hiroshiba.jp/)
2. Start VOICEVOX before using the add-on (runs on `http://localhost:50021`)
3. Test connection and select preferred voice in settings

#### **AivisSpeech** (Free, Japanese-focused)
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
3. Adjust the speed between 0.5x to 3x in 0.1x intervals

## 🎯 Usage

### During Review
1. Review your card as normal
2. Click **"Generate explanation"** button when answer is shown
3. Wait for text generation and audio synthesis to complete
4. New content appears automatically on your card 

### Batch Processing
1. Open the Anki browser
2. Select cards you want to process
3. Go to `Edit > Batch Generate AI Explanations`
4. Monitor progress and review results

## 🛠️ Requirements

- **Anki**: Version 2.1.50+ (tested with Anki 25+)
- **OpenAI API Key**: With sufficient credits
- **Internet Connection**: For API calls
- **TTS Engine** (optional): Choose from supported engines for audio generation

## 🔧 Troubleshooting

### Common Issues

**My cards keep failing to generate. Why?**

This could be because,
- Your OpenAI API Key has expired.
- You ran out of OpenAI API credits.
- Your prompt is misconfigured. Remember that {sentence}, {word}, and {definition} should all be in lowercase. It's case sensitive. There should be no other {x} in your prompt.

**The audio did not generate. Why?**

If you're using VoiceVox or AivisSpeech, you must ensure you have it running in the background.

If you're using ElevenLabs or OpenAI TTS then sure you have an internet connection.

**Why cards fail to generate in bulk after a few cards. Why?**

If you recently made an OpenAI Developer account then your rate limit will be low for the first few days. I'd recommend waiting a few days and only generating a few cards at a time.

### Debug Information
Check these files in your add-on directory for detailed error information:
- `debug_log.txt` - General operation logs
- `crash_log.txt` - System crash information

## 🎓 Learning Resources

**Want to learn more about effective language learning?**

Check out [Matt vs Japan's Immersion Dojo](https://www.skool.com/mattvsjapan/about?ref=837f80b041cf40e9a3979cd1561a67b2) for advanced language learning theory and community support.

## 📝 License

This project is open source. See the repository for license details.

## 🤝 Contributing

Found a bug or have a feature request? Please open an issue on the GitHub repository.

---

*Happy language learning! 🌍📚* 
