# 🚀 How to Run the Browser Agent

## Quick Start (3 Steps)

### Step 1: Install Dependencies

Open terminal/PowerShell in the project folder and run:

```bash
pip install -r requirements.txt
playwright install chromium
```

**What this does:**
- Installs Python packages (playwright, google-generativeai, python-dotenv)
- Downloads Chromium browser (~150MB, one-time)

---

### Step 2: Set Up Your API Key

Make sure you have a `.env` file in the project root with:

```env
GEMINI_API_KEY=your_actual_api_key_here
```

**To get an API key:**
1. Go to https://makersuite.google.com/app/apikey
2. Sign in with Google
3. Click "Create API Key"
4. Copy the key
5. Paste it in your `.env` file

**Optional settings in `.env`:**
```env
FORM_URL=https://forms.gle/6Nc6QaaJyDvePxLv7
HEADLESS=false
BROWSER_TIMEOUT=30000
```

---

### Step 3: Run the Agent

```bash
python main.py
```

**That's it!** The browser will open and fill the form automatically.

---

## What Happens When You Run

1. ✅ Browser opens (you'll see it)
2. ✅ Navigates to the Google Form
3. ✅ **PERCEPTION**: Detects and classifies all fields
4. ✅ **DECISION**: AI decides what to fill in each field
5. ✅ **EXECUTION**: Fills each field automatically
6. ✅ Browser stays open for 2 minutes for review

---

## Troubleshooting

### ❌ "ModuleNotFoundError"
**Fix:**
```bash
pip install -r requirements.txt
```

### ❌ "GEMINI_API_KEY not found"
**Fix:**
- Make sure `.env` file exists in project root
- Check the variable name is exactly `GEMINI_API_KEY` (case-sensitive)
- No quotes around the value: `GEMINI_API_KEY=your_key` (not `GEMINI_API_KEY="your_key"`)

### ❌ "Executable doesn't exist" or browser won't start
**Fix:**
```bash
playwright install chromium
```

### ❌ Browser opens but form doesn't fill
**Check:**
- Is your API key valid?
- Check console output for error messages
- Try increasing `BROWSER_TIMEOUT` in `.env`

---

## Verify Setup (Optional)

Run this to check everything is configured:

```bash
python check_setup.py
```

This will verify:
- ✅ All files present
- ✅ Dependencies installed
- ✅ `.env` file configured
- ✅ Browser installed

---

## Example Output

When you run `python main.py`, you'll see:

```
============================================================
🤖 Browser Agent - Google Form Filler
============================================================
Form URL: https://forms.gle/6Nc6QaaJyDvePxLv7
Headless mode: False

🚀 Starting browser...
Navigating to: https://forms.gle/6Nc6QaaJyDvePxLv7
✓ Form loaded successfully

============================================================
STEP 1: PERCEPTION - Understanding Form Structure
============================================================
🔍 [Perception] Analyzing form structure...
✓ [Perception] Detected 6 fields
   Field 0: 'What is the name of your Master?' - name (text)
   Field 1: 'Which course is he/she taking?' - choice (select)
   ...

============================================================
STEP 2: DECISION - Deciding What to Fill
============================================================
🤖 [Decision] Deciding value for: 'What is the name of your Master?'
   Purpose: name, Type: text
   Decision: 'John Doe'
   ...

============================================================
STEP 3: EXECUTION - Filling Form Fields
============================================================
📝 Filling field 1/6: 'What is the name of your Master?'
   Decision: 'John Doe'
   ✓ Filled 'What is the name of your Master?' with 'John Doe'
...

============================================================
✅ Form filling completed! Filled 6/6 fields
============================================================
```

---

## Configuration Options

Edit `.env` to customize:

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Your Gemini API key (required) | - |
| `FORM_URL` | URL of form to fill | `https://forms.gle/6Nc6QaaJyDvePxLv7` |
| `HEADLESS` | Run browser in background | `false` |
| `BROWSER_TIMEOUT` | Browser timeout (ms) | `30000` |

---

## Need Help?

1. Check `RUN_STEPS.md` for detailed troubleshooting
2. Check `README.md` for full documentation
3. Check `ARCHITECTURE.md` to understand how it works

---

## That's It! 🎉

The agent will:
- ✅ Detect all form fields
- ✅ Use AI to decide what to fill
- ✅ Fill the form automatically
- ✅ Leave browser open for 2 minutes for review

You can then manually submit the form if needed!


