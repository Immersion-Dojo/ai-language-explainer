# GPT Explainer for Anki

This addon generates explanations for Japanese language learning cards using OpenAI's GPT-4o.

## Features

- Automatically generates explanations for words based on their definition, example sentence, and context
- Creates high-quality audio recordings of the explanations using VOICEVOX (requires VOICEVOX to be running)
- Works with any note type (configurable fields)
- Adds a button during review to generate explanations on demand

## Setup

1. Install the addon through Anki's addon manager
2. Go to Tools > GPT Language Explainer Settings
3. Select your note type (e.g., "Ray's Sentence Mining")
4. Configure the input fields (word, sentence, definition, picture)
5. Configure the output fields (explanation, explanation audio)
6. Enter your OpenAI API key
7. Customize the GPT prompt if desired
8. Click Save

## Audio Generation with VOICEVOX

This addon now uses VOICEVOX for audio generation. VOICEVOX is a free Japanese text-to-speech software that produces high-quality natural-sounding voices.

To use the audio generation feature:

1. Download and install VOICEVOX from the [official website](https://voicevox.hiroshiba.jp/)
2. Start VOICEVOX before generating explanations in Anki
3. VOICEVOX must be running in the background for audio generation to work
4. The addon will automatically detect if VOICEVOX is running and use it for audio generation

If VOICEVOX is not running, the addon will display a message and continue without generating audio.

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