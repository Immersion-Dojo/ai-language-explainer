# Debugging Instructions for GPT Language Explainer

If you're experiencing crashes with the addon, follow these steps to collect debugging information:

## 1. Reproduce the Crash

1. Make sure you're using version 1.3.1 or later of the addon
2. Try to reproduce the crash by:
   - Selecting a card in the browser and generating an explanation, or
   - Clicking the "Generate GPT Explainer" button during review

## 2. Collect Debug Logs

After Anki crashes, several debug log files will be created in the addon directory:

- `debug_log.txt` - Contains detailed logs from the audio generation process
- `process_debug.txt` - Contains detailed logs from the note processing
- `error_log.txt` - Contains general error information
- `crash_log.txt` - Contains system information

## 3. Find the Addon Directory

1. Open Anki
2. Go to Tools > Add-ons
3. Select "GPT Language Explainer"
4. Click "View Files"

This will open the addon directory where the log files are stored.

## 4. Share the Debug Logs

1. Compress (zip) all the log files
2. Share them with the developer along with:
   - A description of what you were doing when the crash occurred
   - Your Anki version
   - Your operating system version
   - Any error messages you saw

## Additional Debugging Steps

If Anki crashes immediately and you can't access the log files, you can try running Anki from the terminal to see any error messages:

### On macOS:
1. Open Terminal
2. Run: `/Applications/Anki.app/Contents/MacOS/Anki`
3. Try to reproduce the crash
4. Copy any error messages that appear in the terminal

### On Windows:
1. Open Command Prompt
2. Navigate to your Anki installation directory
3. Run: `anki.exe`
4. Try to reproduce the crash
5. Copy any error messages that appear in the command prompt

### On Linux:
1. Open Terminal
2. Run: `anki`
3. Try to reproduce the crash
4. Copy any error messages that appear in the terminal 