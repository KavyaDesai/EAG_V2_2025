"""
Setup verification script.
Run this to check if your environment is configured correctly.
"""

import os
import sys
from pathlib import Path

def check_file_exists(filename):
    """Check if a file exists."""
    exists = Path(filename).exists()
    status = "✅" if exists else "❌"
    print(f"{status} {filename}")
    return exists

def check_env_setup():
    """Check .env file setup."""
    env_exists = check_file_exists(".env")
    
    if not env_exists:
        print("\n⚠️  .env file not found!")
        print("   Create it by copying env.example:")
        print("   Windows: Copy-Item env.example .env")
        print("   Linux/Mac: cp env.example .env")
        return False
    
    # Try to load and check for API key
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key or api_key == "your_gemini_api_key_here":
            print("\n⚠️  GEMINI_API_KEY not set in .env file!")
            print("   Edit .env and add your Gemini API key")
            return False
        else:
            print(f"   ✅ GEMINI_API_KEY is set (length: {len(api_key)})")
            return True
    except ImportError:
        print("\n⚠️  python-dotenv not installed")
        return False

def check_dependencies():
    """Check if required packages are installed."""
    print("\n📦 Checking dependencies...")
    
    required_packages = {
        "playwright": "playwright",
        "google.generativeai": "google-generativeai",
        "dotenv": "python-dotenv"
    }
    
    all_installed = True
    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - Install with: pip install {package}")
            all_installed = False
    
    return all_installed

def check_playwright_browser():
    """Check if Playwright browser is installed."""
    print("\n🌐 Checking Playwright browser...")
    
    try:
        from playwright.sync_api import sync_playwright
        playwright = sync_playwright().start()
        try:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
            playwright.stop()
            print("   ✅ Chromium browser installed")
            return True
        except Exception as e:
            print(f"   ❌ Browser not installed: {e}")
            print("   Install with: playwright install chromium")
            return False
    except ImportError:
        print("   ⚠️  Cannot check (playwright not installed)")
        return False

def main():
    """Run all checks."""
    print("=" * 60)
    print("🔍 Browser Agent Setup Verification")
    print("=" * 60)
    
    print("\n📁 Checking project files...")
    files_ok = all([
        check_file_exists("main.py"),
        check_file_exists("browser_agent.py"),
        check_file_exists("gemini_client.py"),
        check_file_exists("prompts.py"),
        check_file_exists("requirements.txt"),
        check_file_exists("env.example")
    ])
    
    deps_ok = check_dependencies()
    env_ok = check_env_setup()
    browser_ok = check_playwright_browser()
    
    print("\n" + "=" * 60)
    if all([files_ok, deps_ok, env_ok, browser_ok]):
        print("✅ All checks passed! You're ready to run the agent.")
        print("\nRun: python main.py")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("\nQuick fixes:")
        if not deps_ok:
            print("   pip install -r requirements.txt")
        if not browser_ok:
            print("   playwright install chromium")
        if not env_ok:
            print("   Create .env file and add your GEMINI_API_KEY")
    print("=" * 60)

if __name__ == "__main__":
    main()

