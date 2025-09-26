
import os, sys
print("GEMINI_API_KEY present in environment? ->", bool(os.getenv("GEMINI_API_KEY")))
try:
    from google import genai
except Exception as e:
    print("IMPORT ERROR:", e)
    sys.exit(1)
try:
    client = genai.Client()
    resp = client.models.generate_content(model="gemini-2.0-flash", contents="Answer the question: how r u?")
    #print("GENIE RESP (repr):", repr(resp))
    print("GENIE TEXT (get attr):", getattr(resp, "text", None))
except Exception as e:
    print("LLM CALL ERROR:", e)

