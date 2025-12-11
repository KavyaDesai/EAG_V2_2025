"""
Main entry point for the browser agent.
This script orchestrates the form filling process.
"""

import os
import sys
from dotenv import load_dotenv
from browser_agent import BrowserAgent
from gemini_client import GeminiClient

# Load environment variables
load_dotenv()


def main():
    """Main function to run the browser agent."""
    
    # Get configuration from environment
    form_url = os.getenv("FORM_URL", "https://forms.gle/6Nc6QaaJyDvePxLv7")
    headless = os.getenv("HEADLESS", "false").lower() == "true"
    timeout = int(os.getenv("BROWSER_TIMEOUT", "30000"))
    
    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY not found in .env file")
        print("Please create a .env file with your Gemini API key.")
        print("You can copy .env.example to .env and fill in your API key.")
        sys.exit(1)
    
    print("=" * 60)
    print("🤖 Browser Agent - Google Form Filler")
    print("=" * 60)
    print(f"Form URL: {form_url}")
    print(f"Headless mode: {headless}")
    print()
    
    # Initialize components
    try:
        gemini_client = GeminiClient()
        browser_agent = BrowserAgent(
            headless=headless,
            timeout=timeout,
            gemini_client=gemini_client
        )
        
        # Start browser
        print("🚀 Starting browser...")
        browser_agent.start_browser()
        
        # Fill the form
        success = browser_agent.fill_form_with_ai(form_url)
        
        if success:
            print("\n" + "=" * 60)
            print("✅ Form filling process completed!")
            print("=" * 60)
            print("\nThe browser will remain open for 2 minutes so you can review.")
            print("You can manually submit the form if needed.")
            
            # Keep browser open for review
            import time
            time.sleep(120)  # 2 minutes
        else:
            print("\n" + "=" * 60)
            print("⚠️  Form filling encountered issues.")
            print("=" * 60)
            print("\nThe browser will remain open for 30 seconds for debugging.")
            import time
            time.sleep(30)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if 'browser_agent' in locals():
            print("\n🧹 Cleaning up...")
            browser_agent.close_browser()
            print("✅ Browser closed")


if __name__ == "__main__":
    main()

