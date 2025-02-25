# GPT Explaination Generator for Anki

This addon generates explainations for Japanese language learning cards using OpenAI's GPT-4o.

## Features

- Automatically generates explainations for words based on their definition, example sentence, and context
- Analyzes images in your cards to provide more contextual explainations
- Creates high-quality audio recordings of the explainations using VOICEVOX (requires VOICEVOX to be running)
- Works with any note type (configurable fields)
- Adds a button during review to generate explainations on demand
- Option to preserve existing explainations and audio (avoid overriding)

## Setup

1. Install the addon through Anki's addon manager
2. Go to Tools > GPT Explaination Settings
3. Select your note type (e.g., "Ray's Sentence Mining")
4. Configure the input fields (word, sentence, definition, picture)
5. Configure the output fields (explaination, explaination audio)
6. Enter your OpenAI API key
7. Customize the GPT prompt if desired
8. Click Save

## Audio Generation with VOICEVOX

This addon now uses VOICEVOX for audio generation. VOICEVOX is a free Japanese text-to-speech software that produces high-quality natural-sounding voices.

To use the audio generation feature:

1. Download and install VOICEVOX from the [official website](https://voicevox.hiroshiba.jp/)
2. Start VOICEVOX before generating explainations in Anki
3. VOICEVOX must be running in the background for audio generation to work
4. The addon will automatically detect if VOICEVOX is running and use it for audio generation

If VOICEVOX is not running, the addon will display a message and continue without generating audio.

## Usage

### During Review

When reviewing cards of your configured note type, a "Generate Explaination" button will appear at the top of the screen. Click it to generate an explaination for the current card.

If the card already has an explaination or audio, you'll be asked whether you want to override it.

## Image Processing

The addon includes the ability to analyze images in your cards. When an image is present in the configured picture field, it will be sent to GPT-4o for analysis, allowing the AI to provide more contextually relevant explainations based on the visual content.

## Requirements

- Anki 25+
- An OpenAI API key with access to GPT-4o
- Internet connection
- VOICEVOX (for audio generation)

## Troubleshooting

If you encounter any issues:

1. Make sure your OpenAI API key is valid and has sufficient credits
2. Check that the configured fields exist in your note type
3. Ensure you have an active internet connection
4. If images aren't being processed correctly, make sure they are in a supported format (JPG, PNG, etc.)
5. For audio generation issues, verify that VOICEVOX is running and accessible at http://localhost:50021
6. Check the error_log.txt file in the addon directory for detailed error information

## Changelog

### Version 1.4.0
- Removed bulk processing functionality to simplify the addon
- Improved button placement during review
- Enhanced error handling and logging

### Version 1.3.4
- Reimplemented audio generation using VOICEVOX, a free Japanese text-to-speech software
- Added VOICEVOX status indicators in the settings dialog
- Improved error handling for audio generation

### Version 1.3.3
- Completely removed OpenAI-based audio generation functionality to address stability issues on macOS

### Version 1.3.2
- Temporarily disabled audio generation to troubleshoot stability issues on macOS

### Version 1.3.1
- Added comprehensive error handling and logging
- Fixed stability issues on macOS, especially with audio file generation
- Added safeguards to prevent crashes during note processing

### Version 1.2.0
- Added option to preserve existing explainations and audio

### Version 1.1.0
- Added image analysis capability

## Credits

Created by Ray 