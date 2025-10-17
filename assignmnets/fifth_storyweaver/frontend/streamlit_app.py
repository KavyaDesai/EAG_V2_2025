# frontend/streamlit_app.py
import os
import json
import requests
import streamlit as st

# ====== Config ======
API_BASE = os.getenv("STORY_API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="StoryWeaver", page_icon="📚", layout="centered")

st.title("📚 StoryWeaver — Kid-friendly Story Builder")
st.caption("Powered by Gemini Flash · Agentic planning + strict JSON")

with st.form("story_form"):
    st.subheader("🧒 Preferences (optional)")
    child_name = st.text_input("Child's name", "")
    favorite_animal = st.text_input("Favorite animal", "")
    favorite_setting = st.text_input("Favorite setting", "")
    tone = st.selectbox("Tone", ["", "funny", "adventurous", "calm", "mysterious"])

    st.subheader("💡 Story Idea")
    topic = st.text_input("Prompt (e.g., 'A rabbit and a turtle become friends')", "")

    colA, colB = st.columns([1,1])
    with colA:
        model = st.text_input("Model", "gemini-2.0-flash")
    with colB:
        submitted = st.form_submit_button("✨ Generate Story")

if submitted:
    if not topic.strip():
        st.warning("Please enter a story idea (topic).")
    else:
        with st.spinner("Weaving your story..."):
            payload = {
                "topic": topic.strip(),
                "model": model.strip(),
                "preferences": {
                    "child_name": child_name or None,
                    "favorite_animal": favorite_animal or None,
                    "favorite_setting": favorite_setting or None,
                    "tone": tone or None,
                },
            }
            try:
                resp = requests.post(f"{API_BASE}/generate", json=payload, timeout=60)
                if resp.status_code != 200:
                    st.error(f"Server error: {resp.status_code} — {resp.text}")
                else:
                    data = resp.json()
                    if not data.get("ok"):
                        st.error("Response not ok.")
                    else:
                        story = data["data"]["story"]
                        moral = data["data"]["moral"]
                        plan = data["data"]["plan"]
                        self_check = data["data"]["self_check"]

                        # ======= Display: Story (row 1) =======
                        st.subheader(story.get("title", "Your Story"))
                        st.write(story.get("text", ""))

                        # ======= Display: Moral (row 2) =======
                        st.markdown("---")
                        st.subheader("🌟 Moral of the story")
                        st.success(moral)

                        # Optional: collapsible details (plan + checks)
                        with st.expander("Show planning & self-checks"):
                            st.json({"plan": plan, "self_check": self_check})

            except requests.RequestException as e:
                st.error(f"Could not reach API at {API_BASE}. Error: {e}")
