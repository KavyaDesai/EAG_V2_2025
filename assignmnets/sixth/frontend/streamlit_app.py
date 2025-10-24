# frontend/streamlit_app.py
import os
import json
from typing import List

import requests
import streamlit as st

# ----------------------------
# Config
# ----------------------------
st.set_page_config(
    page_title="Agent-Fable Kids Story Maker",
    page_icon="📚",
    layout="centered",
)

DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT_SECS = 90

# ----------------------------
# Helpers
# ----------------------------
def _backend_url(path: str) -> str:
    base = st.session_state.get("backend_url", DEFAULT_BACKEND_URL)
    return f"{base}{path}"

def parse_csv(value: str) -> List[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]

def call_health() -> dict:
    try:
        r = requests.get(_backend_url("/health"), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}

def call_health_llm() -> dict:
    try:
        r = requests.get(_backend_url("/health/llm"), timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"llm_ok": False, "error": str(e)}

def post_bootstrap_preferences(user_id: str, preferences: dict) -> dict:
    payload = {"user_id": user_id, "preferences": preferences}
    r = requests.post(_backend_url("/bootstrap/preferences"), json=payload, timeout=TIMEOUT_SECS)
    r.raise_for_status()
    return r.json()

def post_generate(user_id: str, topic: str) -> dict:
    r = requests.post(_backend_url("/stories/generate"),
                      json={"user_id": user_id, "topic": topic},
                      timeout=TIMEOUT_SECS)
    r.raise_for_status()
    return r.json()

def story_as_txt(resp: dict) -> str:
    plan = resp.get("plan", {})
    story = resp.get("story", {})
    critique = resp.get("critique", {})

    lines = []
    if story.get("title"):
        lines.append(story["title"])
        lines.append("=" * len(story["title"]))
        lines.append("")
    if story.get("story"):
        lines.append(story["story"].strip())
        lines.append("")
    if story.get("moral"):
        lines.append(f"Moral: {story['moral'].strip()}")
        lines.append("")

    lines.append("— — —")
    lines.append("Plan")
    lines.append("— — —")
    for k in ("title", "setting", "characters", "outline", "target_words", "reading_level", "moral"):
        if k in plan and plan[k] not in (None, "", []):
            lines.append(f"{k}: {json.dumps(plan[k], ensure_ascii=False)}")

    lines.append("")
    lines.append("— — —")
    lines.append("Critique")
    lines.append("— — —")
    for k in ("ok", "reasons", "suggestions", "flagged_themes"):
        if k in critique and critique[k] not in (None, "", []):
            lines.append(f"{k}: {json.dumps(critique[k], ensure_ascii=False)}")

    return "\n".join(lines).strip() + "\n"

# ----------------------------
# Sidebar: backend + health
# ----------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    backend_url = st.text_input("Backend URL", value=DEFAULT_BACKEND_URL, help="FastAPI server base URL")
    st.session_state["backend_url"] = backend_url.rstrip("/")

    cols = st.columns(2)
    with cols[0]:
        if st.button("Ping API"):
            h = call_health()
            st.success("Backend OK") if h.get("status") == "ok" else st.error(h)
    with cols[1]:
        if st.button("Ping LLM"):
            h = call_health_llm()
            st.success("LLM OK") if h.get("llm_ok") else st.error(h)

    st.markdown("---")
    st.caption("Tip: set env var `BACKEND_URL` to override the default.")

# ----------------------------
# Main UI
# ----------------------------
st.title("📚 Agent-Fable Kids Story Maker")
st.caption("Planner • Author • Critic — Cognitive Layers (Preferences first)")


c1, c2 = st.columns(2)
with c1:
    user_id = st.text_input("User ID", value=st.session_state.get("user_id", "kavya"))
with c2:
    location = st.text_input("Location (optional)", value=st.session_state.get("location", "Bengaluru"))

# Track which users have saved preferences in this session
if "prefs_saved_users" not in st.session_state:
    st.session_state["prefs_saved_users"] = set()

def save_prefs():
    if not user_id.strip():
        st.error("User ID is required.")
        return
    # Only send location as a preference from this section
    preferences = {
        "location": (location.strip() or None),
    }
    resp = post_bootstrap_preferences(user_id.strip(), preferences)
    st.session_state["user_id"] = user_id.strip()
    st.session_state["location"] = location
    st.session_state["prefs_saved_users"].add(user_id.strip())
    st.success("Preferences saved.")
    return resp



st.markdown("---")

# ---- 2) Story Preferences ----
st.subheader("Story Preferences")
pc1, pc2 = st.columns(2)
with pc1:
    target_words = st.slider("Target words", min_value=150, max_value=1200, value=500, step=50)
with pc2:
    reading_level = st.selectbox("Reading level", options=["A1", "A2"], index=1)

avoid_themes_csv = st.text_input("Avoid themes (comma-separated)", value="violence, horror, bullying, romance")
required_moral = st.text_input("Required moral (optional)", value="Kindness and sharing")
required_words_csv = st.text_input("Required words (comma-separated, optional)", value="robot, neighbor, garden")
protagonist_name = st.text_input("Protagonist name (optional)", value="Robo")


save_col, status_col = st.columns([1, 3])
with save_col:
    if st.button("💾 Save Preferences", type="primary", use_container_width=True):
        try:
            save_prefs()
        except requests.HTTPError as he:
            try:
                detail = he.response.json().get("detail")
            except Exception:
                detail = str(he)
            st.error(f"Backend error: {detail}")
        except Exception as e:
            st.error(f"Save failed: {e}")

with status_col:
    saved = user_id.strip() in st.session_state["prefs_saved_users"]
    st.caption("Status: " + ("✅ Saved for this user" if saved else "❌ Not saved — click 'Save Preferences'"))
st.markdown("---")

# ---- 3) Topic + Generate ----
st.subheader("Generate Story")

preset = st.selectbox(
    "Quick preset (optional)",
    ["— none —",
     "A shy squirrel learns to make friends",
     "A curious robot learns to share",
     "The little cloud who brings shade",
     "A kite that was afraid of the sky",
     "The classroom plant that loved music"],
    index=0,
)

topic = st.text_area(
    "Story topic",
    value="" if preset == "— none —" else preset,
    height=80,
    placeholder="e.g., A curious robot learns to share",
)

# Whether preferences saved for this user in this session
prefs_saved_for_user = (user_id.strip() in st.session_state["prefs_saved_users"]) 

# Button to generate
gen_btn = st.button(
    "✨ Generate Story",
    type="primary",
    use_container_width=True,
    disabled=not prefs_saved_for_user
)

if gen_btn:
    if not topic or len(topic.strip()) < 3:
        st.warning("Please enter a topic (at least 3 characters).")
        st.stop()

    # Compose preferences from UI
    client_story_prefs = {
        "target_words": target_words,
        "reading_level": reading_level,
        "avoid_themes": parse_csv(avoid_themes_csv),
        "required_moral": (required_moral.strip() or None),
        "required_words": parse_csv(required_words_csv),
        "protagonist_name": (protagonist_name.strip() or None),
        # also include location if you want it considered:
        "location": (location.strip() or None),
    }

    try:
        with st.spinner("Saving preferences…"):
            # 🔁 ensure backend memory has the latest prefs
            post_bootstrap_preferences(user_id.strip(), client_story_prefs)

        with st.spinner("Planning… Writing… Critiquing…"):
            resp = post_generate(user_id.strip(), topic.strip())
    except requests.HTTPError as he:
        try:
            detail = he.response.json().get("detail")
        except Exception:
            detail = str(he)
        st.error(f"Backend error: {detail}")
        st.stop()
    except Exception as e:
        st.error(f"Request failed: {e}")
        st.stop()

    # ... render response (unchanged) ...


    # Render response
    plan = resp.get("plan", {})
    story = resp.get("story", {})
    critique = resp.get("critique", {})

    st.subheader("📝 Story")
    if story.get("title"):
        st.markdown(f"### {story['title']}")
    meta_cols = st.columns(3)
    with meta_cols[0]:
        st.metric("Reading level", story.get("reading_level", "—"))
    with meta_cols[1]:
        st.metric("Word count", story.get("word_count", 0))
    with meta_cols[2]:
        st.metric("Critic OK", "✅ Yes" if critique.get("ok") else "❌ Needs Fix")

    if story.get("story"):
        st.write(story["story"])
    if story.get("moral"):
        st.info(f"**Moral:** {story['moral']}")

    txt = story_as_txt(resp)
    st.download_button(
        "⬇️ Download .txt",
        data=txt.encode("utf-8"),
        file_name="kids_story.txt",
        mime="text/plain",
        use_container_width=True,
    )

    with st.expander("📋 Plan (Planner)", expanded=False):
        st.markdown(f"**Title:** {plan.get('title', '—')}")
        st.markdown(f"**Setting:** {plan.get('setting', '—')}")
        st.markdown("**Characters:**")
        st.write(plan.get("characters", []))
        st.markdown("**Outline:**")
        st.write(plan.get("outline", []))
        c = st.columns(3)
        with c[0]:
            st.markdown(f"**Target words:** {plan.get('target_words', '—')}")
        with c[1]:
            st.markdown(f"**Reading level:** {plan.get('reading_level', '—')}")
        with c[2]:
            st.markdown(f"**Moral:** {plan.get('moral', '—')}")

    with st.expander("🔎 Critique (Critic)", expanded=True):
        ok = critique.get("ok", False)
        st.markdown("**Result:** " + ("✅ OK" if ok else "❌ Needs improvement"))
        reasons = critique.get("reasons") or []
        suggestions = critique.get("suggestions") or []
        flagged = critique.get("flagged_themes") or []
        if reasons:
            st.markdown("**Reasons:**")
            for r in reasons:
                st.write(f"- {r}")
        if suggestions:
            st.markdown("**Suggestions:**")
            for s in suggestions:
                st.write(f"- {s}")
        if flagged:
            st.markdown("**Flagged themes:**")
            for f in flagged:
                st.write(f"- {f}")

st.markdown("---")
st.caption("Agent-Fable A Kids Story Maker • Multi-Agentic story generation with Planner • Author • Critic ")
