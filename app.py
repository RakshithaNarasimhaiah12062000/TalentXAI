import os
import uuid
import tempfile
from typing import List, Dict

import streamlit as st
from streamlit_mic_recorder import mic_recorder
import entxp
from frontend.bedrock_agent import call_master_agent as call_master_agent_text, synthesize_voice
from voice_pipeline import handle_voice_interaction

# Page config
st.set_page_config(page_title="SparkPath OS", layout="wide")

# Audio cache
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "audio_cache")
os.makedirs(AUDIO_DIR, exist_ok=True)

# -----------------------------------
# Read query params to handle "go next"
# -----------------------------------
if "go_next" not in st.session_state:
    st.session_state.go_next = False

params = st.query_params
if params.get("next", ["false"])[0].lower() == "true":
    st.session_state.go_next = True

# -----------------------------------
# Avatar Selector Page
# -----------------------------------
def avatar_selector_page():
    st.title("🎨 Talent X AI")

    avatar_options = {
        "A dancer": "https://models.readyplayer.me/6917ea365f9f523e500b3e38.glb",
        "A music producer": "https://models.readyplayer.me/6917f36b672cca15c2f8b45b.glb",
        "A film director": "https://models.readyplayer.me/6917f1a648062250a41a8134.glb",
        "A gamer": "https://models.readyplayer.me/6917e5f7132e61458ccd4798.glb",
        "A fashion influencer": "https://models.readyplayer.me/6917ed4628f4be8b0cd2b12a.glb",
        "Don't know yet": "https://models.readyplayer.me/placeholder.glb"
    }
    emoji_icons = {
        "A dancer": "🕺",
        "A music producer": "🎧",
        "A film director": "🎬",
        "A gamer": "🎮",
        "A fashion influencer": "👗",
        "Don't know yet": "❓"
    }

    if "selected" not in st.session_state:
        st.session_state.selected = "A fashion influencer"

    selected = st.session_state.selected
    labels = list(avatar_options.keys())
    positions = [(-350, 60), (-200, 10), (-50, -20), (100, -20), (250, 10), (400, 60)]
    center_index = len(labels) // 2
    labels.remove(selected)
    labels.insert(center_index, selected)

    # Build HTML
    html = """
    <style>
      body { background:#0a0420; color:white; font-family:Inter,sans-serif; }
      .arc-container { position: relative; width: 100%; height: 360px; margin-top: 20px;
                       display: flex; justify-content: center; }
      .avatar { width: 140px; height: 170px; border-radius: 50%; background:#1c1c3c;
                color:white; font-size:55px; display:flex; justify-content:center;
                align-items:center; opacity: 0.5; transition:0.25s; cursor:pointer; }
      .avatar:hover { opacity:1; transform:scale(1.25); z-index:10;
                      box-shadow:0 0 22px #61f0ff; border:3px solid #61f0ff; }
      .role-label { margin-top: 6px; font-size: 15px; color:#d7e9ff; opacity:0.9; }
      .center-glow { margin: 0 auto; width: 330px; height: 330px;
                     border-radius: 50%; border: 6px solid #6cf3ff;
                     box-shadow: 0 0 38px #6cf3ff; overflow: hidden;
                     position: relative; top: -40px; cursor: pointer; }
    </style>

    <div class="arc-container">
    """
    for (label, (x, y)) in zip(labels, positions):
        html += f"""
        <div style="position:absolute; left:calc(50% + {x}px); top:{y}px; text-align:center;">
          <div class='avatar'
               onmouseover="document.getElementById('model').src='{avatar_options[label]}';">
            {emoji_icons[label]}
          </div>
          <div class="role-label">{label}</div>
        </div>
        """

    html += "</div>"

    # Center glow model
    html += f"""
    <div class="center-glow">
      <model-viewer id="model" src="{avatar_options[selected]}"
                    auto-rotate camera-controls
                    style="width:100%; height:100%;">
      </model-viewer>
    </div>

    <script type="module" src="https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"></script>
    """

    # Render the avatar HTML
    st.components.v1.html(html, height=800)

    # -------------------------------------------------
    # Hidden button below the center avatar
    # -------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)  # small spacing
    if st.button("→", key="goto_voice_copilot"):
        st.session_state.go_next = True
        st.experimental_rerun()


# =====================================================================
# Voice Copilot
# =====================================================================
def voice_copilot_tab():
    st.title("🎤 SparkPath – Voice Career Copilot")

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "history" not in st.session_state:
        st.session_state.history = []

    session_id = st.session_state.session_id
    st.subheader("💬 Conversation")
    for turn in st.session_state.history:
        label = "🧑 You" if turn["role"] == "user" else "🎬 Agent"
        st.markdown(f"**{label}:** {turn['text']}")
        if turn.get("audio_path") and os.path.exists(turn["audio_path"]):
            st.audio(turn["audio_path"], format="audio/mp3")

    st.markdown("---")
    if st.button("🔁 Reset conversation"):
        st.session_state.history = []
        st.session_state.session_id = str(uuid.uuid4())
        st.experimental_rerun()

    user_text = st.text_input("Type your message:", key="typed_input")
    if st.button("Send text"):
        if user_text.strip():
            st.session_state.history.append({"role": "user", "text": user_text, "audio_path": None})
            agent_reply = call_master_agent_text(user_text, user_id=session_id)
            try:
                audio_bytes = synthesize_voice(agent_reply)
                temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                temp_audio.write(audio_bytes)
                reply_audio_path = temp_audio.name
            except Exception as e:
                reply_audio_path = None
            st.session_state.history.append({"role": "agent", "text": agent_reply, "audio_path": reply_audio_path})
            st.experimental_rerun()

    st.markdown("---")
    st.markdown("### 🎤 Speak your message")
    audio = mic_recorder(start_prompt="🎙️ Start recording", stop_prompt="🛑 Stop", key="mic1")
    if audio:
        st.success("Recording captured!")
        if st.button("Send voice to agent"):
            with st.spinner("…"):
                user_audio_path = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}_user.wav")
                with open(user_audio_path, "wb") as f:
                    f.write(audio["bytes"])

                reply_audio_path = os.path.join(AUDIO_DIR, f"{uuid.uuid4()}_reply.mp3")
                user_text, agent_reply, final_audio = handle_voice_interaction(
                    user_audio_path, reply_audio_path, session_id
                )
                if not final_audio:
                    final_audio = reply_audio_path
                st.session_state.history.append({"role": "user", "text": user_text or "(…)", "audio_path": None})
                st.session_state.history.append({"role": "agent", "text": agent_reply or "(…)", "audio_path": final_audio})
                st.experimental_rerun()
    else:
        st.caption("Press **Start recording**, speak, then press **Stop**.")

# =====================================================================
# MAIN NAVIGATION
# =====================================================================
# =====================================================================
# MAIN NAVIGATION (fixed to always show sidebar)
# =====================================================================
def main():
    # Sidebar always rendered
    with st.sidebar:
        st.markdown("### 🔀 Navigate")
        choice = st.radio("Choose a space:",
            ["🎨 Home", "🎬 Day-in-the-Life Simulation", "✨ Spark Hub", "🎤 Multi Agent Chatbot"]
        )

    # Determine which page to show
    if st.session_state.get("go_next", False):
        voice_copilot_tab()
        st.session_state.go_next = False  # reset after navigating
        return

    # Render based on sidebar choice
    if choice == "🎨 Home":
        avatar_selector_page()
    elif choice == "🎬 Day-in-the-Life Simulation":
        entxp.ent_main()
    elif choice == "✨ Spark Hub":
        entxp.spark_main()
    else:
        voice_copilot_tab()


if __name__ == "__main__":
    main()
