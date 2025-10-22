# frontend/streamlit_app.py
import os
import json
import textwrap
from typing import List, Optional

import requests
import streamlit as st

# ----------------------------
# Config
# ----------------------------
st.set_page_config(
    page_title="Kids Story Maker (Planner • Author • Critic)",
    page_icon="📚",
    layout="centered",
)

DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT_SECS = 90  # generous timeout for LLM calls

# ----------------------------
# Helpers
# ----------------------------
def _backend_url(path: str) -> str:
    base = st.session_state.get("backend_url", DEFAULT_BACKEND_URL)
    return f"{base}{path}"

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

def parse_csv(value: str) -> List[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]

def post_generate(topic: str, prefs: dict) -> dict:
    payload = {
        "topic": topic,
        "preferences": prefs or None,
    }
    r = requests.post(
        _backend_url("/stories/generate"),
        json=payload,
        timeout=TIMEOUT_SECS,
    )
    r.raise_for_status()
    return r.json()

def story_as_txt(resp: dict) -> str:
    """Create a clean .txt export of the final story + moral + plan."""
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
            if h.get("status") == "ok":
                st.success("Backend OK")
            else:
                st.error(h)
    with cols[1]:
        if st.button("Ping LLM"):
            h = call_health_llm()
            if h.get("llm_ok"):
                st.success("LLM OK")
            else:
                st.error(h)

    st.markdown("---")
    st.caption("Tip: set env var `BACKEND_URL` to override the default.")

# ----------------------------
# Main UI
# ----------------------------
st.title("📚 Kids Story Maker")
st.caption("Planner • Author • Critic — for ages 6–10")

# Presets to spark ideas (optional)
preset = st.selectbox(
    "Choose a quick preset (optional)",
    [
        "— none —",
        "A shy squirrel learns to make friends",
        "A curious robot learns to share",
        "The little cloud who brings shade",
        "A kite that was afraid of the sky",
        "The classroom plant that loved music",
    ],
    index=0,
)

topic = st.text_area(
    "Story topic",
    value="" if preset == "— none —" else preset,
    height=80,
    placeholder="e.g., A curious robot learns to share",
)

with st.expander("Preferences (optional)", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        target_words = st.slider("Target words", min_value=150, max_value=1200, value=500, step=50)
    with c2:
        reading_level = st.selectbox("Reading level", options=["A1", "A2"], index=1)

    avoid_themes_csv = st.text_input(
        "Avoid themes (comma-separated)",
        value="violence, horror, bullying, romance",
        help="These will be discouraged by the Critic."
    )
    required_moral = st.text_input(
        "Required moral (optional)",
        value="Kindness and sharing",
        placeholder="e.g., Teamwork matters",
    )
    required_words_csv = st.text_input(
        "Required words (comma-separated, optional)",
        value="robot, neighbor, garden",
        help="We’ll try to weave these into the story."
    )
    protagonist_name = st.text_input(
        "Protagonist name (optional)",
        value="Robo",
    )

submit = st.button("✨ Generate Story", type="primary", use_container_width=True)

# ----------------------------
# Submission handling
# ----------------------------
if submit:
    if not topic or len(topic.strip()) < 3:
        st.warning("Please enter a topic (at least 3 characters).")
        st.stop()

    prefs = {
        "target_words": target_words,
        "reading_level": reading_level,
        "avoid_themes": parse_csv(avoid_themes_csv),
        "required_moral": (required_moral.strip() or None),
        "required_words": parse_csv(required_words_csv),
        "protagonist_name": (protagonist_name.strip() or None),
    }

    with st.spinner("Planning… Writing… Critiquing…"):
        try:
            resp = post_generate(topic.strip(), prefs)
        except requests.HTTPError as he:
            # Try to extract backend error
            try:
                detail = he.response.json().get("detail")
            except Exception:
                detail = str(he)
            st.error(f"Backend error: {detail}")
            st.stop()
        except Exception as e:
            st.error(f"Request failed: {e}")
            st.stop()

    # ----------------------------
    # Render response
    # ----------------------------
    plan = resp.get("plan", {})
    story = resp.get("story", {})
    critique = resp.get("critique", {})

    # Story Section
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

    # Download
    txt = story_as_txt(resp)
    st.download_button(
        "⬇️ Download .txt",
        data=txt.encode("utf-8"),
        file_name="kids_story.txt",
        mime="text/plain",
        use_container_width=True,
    )

    # Plan Section
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

    # Critique Section
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

        # If backend returns a revised_story in critique, show it for comparison
        if critique.get("revised_story"):
            st.markdown("---")
            st.markdown("**Revised by Critic:**")
            rs = critique["revised_story"]
            st.markdown(f"**Title:** {rs.get('title', '—')}")
            st.write(rs.get("story", ""))
            if rs.get("moral"):
                st.info(f"**Moral:** {rs['moral']}")
            cols = st.columns(2)
            with cols[0]:
                st.caption(f"Reading level: {rs.get('reading_level', '—')}")
            with cols[1]:
                st.caption(f"Word count: {rs.get('word_count', '—')}")

# ----------------------------
# Footer
# ----------------------------
st.markdown("---")
st.caption("Kids Story Maker • Multi-Agent (Planner • Author • Critic)")
