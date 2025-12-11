# Browser Agent - Google Form Filler 🤖

An intelligent browser agent that uses Google's Gemini 2.0 Flash AI to automatically analyze and fill out Google Forms. This project demonstrates the integration of AI decision-making with browser automation.

## 🎯 Features

- **AI-Powered Form Analysis**: Uses Gemini 2.0 Flash to understand form structure and determine appropriate values
- **Intelligent Field Detection**: Automatically detects all form fields (text, dropdown, radio buttons, etc.)
- **Smart Form Filling**: AI determines what values to fill based on field labels and context
- **Separated Prompts**: Prompts are stored separately in `prompts.py` for easy modification
- **Error Handling**: Robust error handling with AI-powered recovery suggestions
- **Visual Feedback**: Browser runs in visible mode by default so you can see the process

## 📋 Prerequisites

- Python 3.8 or higher
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- Playwright browser binaries (installed automatically)

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Step 2: Configure Environment

Create a `.env` file in the project root:

```bash
# Copy the example (if available) or create manually
cp env.example .env
```

Edit `.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
FORM_URL=https://forms.gle/6Nc6QaaJyDvePxLv7
HEADLESS=false
BROWSER_TIMEOUT=30000
```

### Step 3: Run the Agent

```bash
python main.py
```

The browser will open, navigate to the form, analyze it with AI, and fill it out automatically.

## 📁 Project Structure

```
.
├── main.py                 # Main entry point
├── browser_agent.py        # Browser automation logic
├── gemini_client.py        # Gemini API integration
├── prompts.py             # AI prompts (separated from code)
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
├── env.example            # Example environment file
├── README.md              # This file
└── ARCHITECTURE.md        # Architecture documentation
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Your Google Gemini API key (required) | - |
| `FORM_URL` | URL of the form to fill | `https://forms.gle/6Nc6QaaJyDvePxLv7` |
| `HEADLESS` | Run browser in headless mode | `false` |
| `BROWSER_TIMEOUT` | Browser operation timeout (ms) | `30000` |

### Customizing Prompts

Edit `prompts.py` to modify how the AI analyzes and fills forms. The prompts are separated from the code for easy customization.

## 🏗️ How It Works

1. **Browser Initialization**: Starts a Chromium browser using Playwright
2. **Form Navigation**: Navigates to the specified Google Form URL
3. **Field Detection**: Uses JavaScript to detect all form fields and their properties
4. **AI Analysis**: Sends form structure to Gemini AI for analysis
5. **Value Determination**: AI determines appropriate values for each field
6. **Form Filling**: Automatically fills each field with the determined values
7. **Review**: Browser stays open for manual review and submission

## 🛠️ Technology Choices

### Why Playwright?

- **Modern & Fast**: Built for modern web applications
- **Reliable**: Better handling of dynamic content than Selenium
- **Cross-browser**: Supports Chromium, Firefox, and WebKit
- **Auto-waiting**: Automatically waits for elements to be ready
- **Great Python API**: Clean and intuitive Python interface

### Why Gemini 2.0 Flash?

- **Fast**: Optimized for speed while maintaining quality
- **Cost-effective**: More affordable than larger models
- **Capable**: Handles form analysis and decision-making well
- **Structured Output**: Can provide JSON responses for parsing

### Why Separate Prompts?

- **Maintainability**: Easy to update prompts without touching code
- **Experimentation**: Quickly test different prompt strategies
- **Version Control**: Track prompt changes separately
- **Collaboration**: Non-developers can modify prompts

## 🐛 Troubleshooting

### "GEMINI_API_KEY not found"
- Make sure you created a `.env` file
- Verify the API key is correctly set in `.env`
- Check that `python-dotenv` is installed

### "Browser not starting"
- Run `playwright install chromium` to install browser binaries
- Check your internet connection
- Try running with `HEADLESS=true` in `.env`

### "Form fields not detected"
- Google Forms may have changed their structure
- Try increasing `BROWSER_TIMEOUT` in `.env`
- Check browser console for JavaScript errors

### "AI not providing values"
- Verify your Gemini API key is valid
- Check your API quota/limits
- Review the prompts in `prompts.py`

## 📝 Example Output

```
============================================================
🤖 Browser Agent - Google Form Filler
============================================================
Form URL: https://forms.gle/6Nc6QaaJyDvePxLv7
Headless mode: False

🚀 Starting browser...
Navigating to: https://forms.gle/6Nc6QaaJyDvePxLv7

🔍 Detecting form fields...
Found 6 form fields

🤖 Analyzing form with Gemini AI...

📝 Filling form fields...
✓ Filled 'What is the name of your Master?' with 'John Doe'
✓ Selected 'EAG' in dropdown
✓ Selected radio option 'Yes'
✓ Filled 'What is his/her email id?' with 'john.doe@example.com'
✓ Filled 'What course is he/her in?' with 'Advanced AI'
✓ Filled 'What is his/her Date of Birth?' with '1990-01-01'

✅ Form filling completed!
============================================================
✅ Form filling process completed!
============================================================
```

## 🔒 Security Notes

- **Never commit `.env` file**: It contains your API key
- **API Key Security**: Keep your Gemini API key secure
- **Form Data**: The agent fills forms with AI-determined values - review before submitting
- **Rate Limits**: Be aware of Gemini API rate limits

## 📚 Additional Resources

- [Playwright Documentation](https://playwright.dev/python/)
- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [Python-dotenv Documentation](https://pypi.org/project/python-dotenv/)

## 🤝 Contributing

Feel free to submit issues or pull requests to improve this project!

## 📄 License

This project is provided as-is for educational and demonstration purposes.

## ⚠️ Disclaimer

This tool is for educational purposes. Always review filled forms before submission. The AI may generate placeholder or example data. Use responsibly and in accordance with Google Forms' terms of service.

