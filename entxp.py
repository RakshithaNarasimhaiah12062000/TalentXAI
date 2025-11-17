import json
import streamlit as st
import boto3
from botocore.config import Config

# ============================
# PAGE CONFIG (GLOBAL)
# ============================

BEDROCK_REGION = "us-east-1"
BEDROCK_MODEL_ID = "meta.llama3-8b-instruct-v1:0"

bedrock_runtime = boto3.client(
    "bedrock-runtime",
    region_name=BEDROCK_REGION,
    config=Config(read_timeout=60, retries={"max_attempts": 3}),
)


def call_bedrock(prompt: str, max_tokens: int = 800, temperature: float = 0.7) -> str:
    """
    Shared Bedrock call for Llama 3-style models.
    Uses schema: prompt / max_gen_len / temperature.
    Returns raw text generation string.
    """
    body = {
        "prompt": prompt,
        "max_gen_len": max_tokens,
        "temperature": temperature,
    }

    response = bedrock_runtime.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=json.dumps(body),
    )

    response_body = json.loads(response["body"].read())
    generation = response_body.get("generation", "")
    print("\n=== Bedrock raw generation ===")
    print(generation)
    print("=== End generation ===\n")
    return generation


# ============================
# JSON HELPER (SHARED)
# ============================

def safe_json_from_model(raw: str):
    """
    Try to extract JSON (list or object) from the raw model string.
    Handles:
    - prose around JSON,
    - ``` fenced blocks,
    - appended markdown.
    """
    raw = raw.strip()

    # 1) direct parse
    try:
        return json.loads(raw)
    except Exception:
        pass

    # 2) inside ``` fences
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("[") or candidate.startswith("{"):
                try:
                    return json.loads(candidate)
                except Exception:
                    continue

    # 3) shortest substring starting at '[' or '{'
    for open_char, close_char in [("[", "]"), ("{", "}")]:
        start = raw.find(open_char)
        if start != -1:
            for end in range(start + 1, len(raw)):
                if raw[end] == close_char:
                    candidate = raw[start: end + 1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        continue

    raise ValueError("Could not extract JSON from model output.")


# ============================================================
# PART 1 · ENT.XP – Day-in-the-Life Experience
# ============================================================

# ---- ENT.XP STATE ----
if "ent_stage" not in st.session_state:
    st.session_state.ent_stage = "landing"

if "ent_role_options" not in st.session_state:
    st.session_state.ent_role_options = []

if "ent_selected_role" not in st.session_state:
    st.session_state.ent_selected_role = None

if "ent_simulations" not in st.session_state:
    st.session_state.ent_simulations = {}  # {role_name: sim_dict}


def ent_go_to(stage: str):
    st.session_state.ent_stage = stage


# ---- ENT.XP HELPERS ----

def ent_generate_role_options_from_ai(profile_text: str):
    """
    Asks Bedrock to generate 3–5 roles in JSON.
    If anything fails, uses fallback roles.
    """
    prompt = f"""
You are a friendly career mentor helping youth discover hidden entertainment careers.

The user profile is:

{profile_text}

Your task:
Suggest EXACTLY 3 to 5 creative entertainment career roles this person might enjoy.

Reply ONLY as a JSON list.
No explanation outside JSON. No prose.

Each item MUST have:
- "role_name"
- "one_sentence_hook"
- "why_it_fits_this_person"
"""

    try:
        raw = call_bedrock(prompt)
        roles = safe_json_from_model(raw)

        if isinstance(roles, list) and len(roles) > 0:
            return roles

        raise ValueError("Parsed roles list is empty.")

    except Exception as e:
        print("ENT.XP Bedrock / JSON error (roles):", repr(e))
        st.toast("Using fallback roles (AI error).", icon="⚠️")

    return [
        {
            "role_name": "Assistant Creative Producer",
            "one_sentence_hook": "You turn ideas and chaos into an actual show.",
            "why_it_fits_this_person": "You enjoy planning, working with others, and being near the action.",
        },
        {
            "role_name": "Community Content Curator",
            "one_sentence_hook": "You find the best stories and help them shine.",
            "why_it_fits_this_person": "You like social media, picking good content, and boosting others’ voices.",
        },
        {
            "role_name": "Studio Session Coordinator",
            "one_sentence_hook": "You keep studio days running smooth and on time.",
            "why_it_fits_this_person": "You’re organized and don’t mind juggling multiple tasks.",
        },
    ]


def ent_generate_day_simulation(role_name: str, fit_reason: str):
    """
    Ask Bedrock to generate a 'day in the life' JSON object for a role.
    Returns a dict with: scenes, key_tasks, key_challenges, growth_path.
    """
    prompt = f"""
You are designing a realistic 'day in the life' story for a youth exploring an entertainment career.

Role: {role_name}

Why this role fits them:
{fit_reason}

Create a typical workday from morning to evening, as JSON with this structure:

{{
  "scenes": [
    {{
      "time_of_day": "9:15 AM",
      "short_title": "Kickoff in the studio lobby",
      "narration": "You grab a coffee and review today's plan with the producer."
    }},
    ...
  ],
  "key_tasks": [
    "Short bullet about an important task",
    "Another key task"
  ],
  "key_challenges": [
    "Short bullet about a real challenge",
    "Another challenge"
  ],
  "growth_path": [
    "Year 1: ...",
    "Year 3: ...",
    "Year 5: ..."
  ]
}}

Guidelines:
- Make 6 to 8 scenes.
- Narration should be 1–2 sentences, present tense, second person ("you ...").
- Keep language simple and encouraging.
- Focus on realistic, not glamorous-only moments.

Reply ONLY with that JSON object. No extra text.
"""

    try:
        raw = call_bedrock(prompt)
        sim = safe_json_from_model(raw)

        if isinstance(sim, list):
            sim = {"scenes": sim}

        if not isinstance(sim, dict):
            raise ValueError("Simulation JSON is not an object or list.")

        return sim

    except Exception as e:
        print("ENT.XP Bedrock / JSON error (simulation):", repr(e))
        st.toast("Could not generate full simulation, showing a simple summary.", icon="⚠️")

        return {
            "scenes": [
                {
                    "time_of_day": "9:00 AM",
                    "short_title": "Getting started",
                    "narration": "You arrive, check messages, and review today's plan.",
                },
                {
                    "time_of_day": "1:00 PM",
                    "short_title": "In the middle of the action",
                    "narration": "You support the team during a busy part of the day, keeping things organized.",
                },
                {
                    "time_of_day": "5:00 PM",
                    "short_title": "Wrap up and reflect",
                    "narration": "You wrap up, note what went well, and think about how you can grow in this role.",
                },
            ],
            "key_tasks": [
                "Support more senior teammates with planning and coordination.",
                "Communicate clearly with people in different roles.",
                "Stay flexible when plans change.",
            ],
            "key_challenges": [
                "Balancing multiple tasks at once.",
                "Handling last-minute changes calmly.",
                "Learning the tools and workflows used by the team.",
            ],
            "growth_path": [
                "Year 1: Learn the basics and find your strengths.",
                "Year 3: Take ownership of small projects or parts of a show.",
                "Year 5: Lead bigger projects and mentor newer teammates.",
            ],
        }


# ---- ENT.XP UI ----

def ent_show_landing():
    st.markdown(
        """
        <div style="text-align:center; padding: 16px 0 4px 0;">
            <div style="
                display:inline-block;
                padding: 6px 14px;
                border-radius: 999px;
                background: rgba(251,191,36,0.1);
                color: #facc15;
                font-size: 0.8rem;
                margin-bottom: 8px;
            ">
                ENT.XP · Day-in-the-Life Simulation
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.title("ENT.XP 🎬")
    st.subheader("See a realistic ‘day in the life’ for entertainment careers.")

    st.markdown(
        """
        - 🧑‍🎤 **Talk about your spark** (what you enjoy)
        - 🎯 **Get matched** to creative roles
        - 🎞️ **Watch your day as a timeline** – from morning to wrap

        Perfect for youth exploring careers with Usher's New Look & Travelers.
        """
    )

    if st.button("Start my ENT.XP journey ✨"):
        ent_go_to("quiz")


def ent_show_quiz():
    st.header("Step 1 · Tell us about your spark")

    interests = st.multiselect(
        "What are you drawn to?",
        ["Music", "Dance", "Gaming", "Film & Video", "Fashion",
         "Social Media", "Writing", "Tech & Editing"],
        key="ent_interests"
    )

    work_style = st.radio(
        "Where do you see yourself?",
        ["On stage / On camera", "Behind the scenes", "A bit of both"],
        key="ent_work_style"
    )

    favorite_day = st.text_area(
        "Describe a recent day that made you feel alive or proud:",
        key="ent_favorite_day",
        placeholder="Example: I helped a friend shoot a TikTok, edited clips, picked music..."
    )

    content_habits = st.text_area(
        "What content do you enjoy making or watching?",
        key="ent_content_habits",
        placeholder="Example: dance reels, gaming highlights, behind-the-scenes vlogs..."
    )

    cols = st.columns(2)
    with cols[0]:
        if st.button("⬅ Back", key="ent_back_from_quiz"):
            ent_go_to("landing")

    with cols[1]:
        if st.button("Show possible roles 🚀", key="ent_show_roles"):
            profile = f"""
Interests: {interests}
Work style: {work_style}
Favorite day: {favorite_day}
Content habits: {content_habits}
"""
            with st.spinner("Reading your spark and mapping it to the entertainment world…"):
                roles = ent_generate_role_options_from_ai(profile)

            st.session_state.ent_role_options = roles
            ent_go_to("roles")


def ent_show_roles():
    st.header("Step 2 · Roles that match your spark ✨")
    st.caption("These are starting points, not boxes. Pick one that *feels* interesting, not perfect.")

    roles = st.session_state.ent_role_options

    if len(roles) == 0:
        st.warning("No roles yet. Go back and fill the spark quiz.")
        if st.button("Back to quiz", key="ent_roles_back_quiz"):
            ent_go_to("quiz")
        return

    for idx, role in enumerate(roles, start=1):
        role_name = role["role_name"]
        hook = role["one_sentence_hook"]
        why_fit = role["why_it_fits_this_person"]

        card_html = f"""
        <div style="
            background: radial-gradient(circle at top left, #1f2937, #020617);
            border-radius: 18px;
            padding: 16px 18px;
            margin-bottom: 14px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.35);
            border: 1px solid rgba(148,163,184,0.35);
        ">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <span style="font-size:0.8rem; opacity:0.8;">Option {idx}</span>
                <span style="
                    font-size:0.75rem;
                    padding: 2px 8px;
                    border-radius: 999px;
                    background: rgba(96,165,250,0.15);
                    color:#bfdbfe;
                ">
                    Entertainment · Creative
                </span>
            </div>
            <div style="font-size: 1.05rem; font-weight: 600; margin-bottom: 4px;">
                {role_name}
            </div>
            <div style="font-size: 0.92rem; opacity: 0.9; margin-bottom: 6px;">
                {hook}
            </div>
            <div style="font-size: 0.85rem; opacity: 0.8;">
                <span style="opacity:0.9; font-weight:500;">Why this fits your spark:</span> {why_fit}
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

        # 🔑 UNIQUE KEY: index + cleaned role_name
        safe_name = role_name.replace(" ", "_")
        if st.button(
            f"👟 Try a day as {role_name}",
            key=f"ent_sim_{idx}_{safe_name}"
        ):
            st.session_state.ent_selected_role = role
            ent_go_to("simulation")
            st.experimental_rerun()

    st.markdown("---")
    if st.button("⬅ Back to quiz", key="ent_roles_back_quiz2"):
        ent_go_to("quiz")


def ent_show_simulation():
    role = st.session_state.ent_selected_role

    if role is None:
        st.warning("Pick a role first from the previous step.")
        if st.button("Back to roles", key="ent_sim_back_roles"):
            ent_go_to("roles")
        return

    role_name = role["role_name"]
    hook = role["one_sentence_hook"]
    fit_reason = role["why_it_fits_this_person"]

    # HERO HEADER
    st.markdown(
        f"""
        <div style="
            background: radial-gradient(circle at top left, #4b5563, #020617);
            border-radius: 22px;
            padding: 18px 18px 16px 18px;
            margin-bottom: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.45);
            border: 1px solid rgba(148,163,184,0.4);
        ">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
                <div>
                    <div style="
                        font-size:0.8rem;
                        padding: 2px 10px;
                        border-radius: 999px;
                        background: rgba(34,197,94,0.18);
                        color:#bbf7d0;
                        display:inline-block;
                        margin-bottom:6px;
                    ">
                        Day-in-the-life · Simulation
                    </div>
                    <div style="font-size:1.25rem; font-weight:700; margin-bottom:4px;">
                        A day as a {role_name}
                    </div>
                    <div style="font-size:0.95rem; opacity:0.9; margin-bottom:6px;">
                        {hook}
                    </div>
                    <div style="font-size:0.85rem; opacity:0.8;">
                        <span style="opacity:0.9; font-weight:500;">Why this matches your spark:</span> {fit_reason}
                    </div>
                </div>
                <div style="font-size:1.8rem; opacity:0.9;">
                    🎧
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Fetch or cache simulation
    if role_name not in st.session_state.ent_simulations:
        with st.spinner("Creating your day-in-the-life story with AI…"):
            sim = ent_generate_day_simulation(role_name, fit_reason)
            st.session_state.ent_simulations[role_name] = sim
    else:
        sim = st.session_state.ent_simulations[role_name]

    scenes = sim.get("scenes", [])
    key_tasks = sim.get("key_tasks", [])
    key_challenges = sim.get("key_challenges", [])
    growth_path = sim.get("growth_path", [])

    # TIMELINE VIEW
    st.subheader("📅 Your day, scene by scene")

    if not scenes:
        st.write("No scenes available yet.")
    else:
        st.caption("Think of this like a TikTok reel broken into little moments across your day.")

        for i, scene in enumerate(scenes, start=1):
            time_of_day = scene.get("time_of_day", "")
            title = scene.get("short_title", "")
            narration = scene.get("narration", "")

            card_html = f"""
            <div style="
                position: relative;
                border-radius: 16px;
                padding: 14px 16px 12px 16px;
                margin-bottom: 12px;
                background: linear-gradient(135deg, #020617, #111827);
                border: 1px solid rgba(148,163,184,0.45);
                box-shadow: 0 8px 20px rgba(0,0,0,0.35);
            ">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <div style="font-size:0.78rem; opacity:0.8;">
                        Scene {i}
                    </div>
                    <div style="
                        font-size:0.78rem;
                        padding: 2px 8px;
                        border-radius: 999px;
                        background: rgba(251,191,36,0.18);
                        color:#fbbf24;
                    ">
                        {time_of_day}
                    </div>
                </div>
                <div style="font-size:0.98rem; font-weight:600; margin-bottom:4px;">
                    {title}
                </div>
                <div style="font-size:0.9rem; line-height:1.4; opacity:0.9;">
                    {narration}
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

    # Spark snapshot
    st.markdown("---")
    st.subheader("⭐ Spark snapshot")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**You’ll probably love this if…**")
        if key_tasks:
            bullets = key_tasks[:3]
            st.markdown("- " + "\n- ".join(bullets))
        else:
            st.markdown(
                "- You like being close to the action\n"
                "- You enjoy helping ideas become real\n"
                "- You don’t mind juggling different tasks"
            )

    with col2:
        st.markdown("**Skills you’ll build here**")
        if key_challenges:
            bullets = key_challenges[:3]
            st.markdown("- " + "\n- ".join(bullets))
        else:
            st.markdown(
                "- Communication with different types of people\n"
                "- Staying calm when plans change\n"
                "- Planning and organizing creative work"
            )

    # Growth path
    st.markdown("---")
    st.subheader("🚀 Where this can take you")

    if growth_path:
        st.markdown("- " + "\n- ".join(growth_path))
    else:
        st.markdown(
            "- **Year 1:** Try out small projects, learn tools, and understand how the team works.\n"
            "- **Year 3:** Own your own segments, lead parts of shoots or campaigns.\n"
            "- **Year 5:** Guide newer creatives, make decisions, and shape the stories you tell."
        )

    # Reflection
    st.markdown("---")
    st.subheader("💬 Quick check-in with yourself")

    st.radio(
        "How does this role feel right now?",
        ["I can totally see myself here", "Maybe, I’m not sure yet", "Doesn’t feel like me"],
        key="ent_role_vibe",
        horizontal=True,
    )

    st.text_area(
        "Any thoughts, questions, or things you’d want to ask someone who already does this job?",
        key="ent_role_notes",
        placeholder="Example: How did you get your first opportunity? Is it okay to be shy in this role? ..."
    )

    cols_bottom = st.columns(2)

    with cols_bottom[0]:
        if st.button("🔁 Try another role", key="ent_try_another_role"):
            ent_go_to("roles")

    with cols_bottom[1]:
        if st.button("🏁 Start over ENT.XP", key="ent_start_over"):
            st.session_state.ent_role_options = []
            st.session_state.ent_selected_role = None
            st.session_state.ent_simulations = {}
            ent_go_to("landing")


def ent_main():
    stage = st.session_state.ent_stage
    if stage == "landing":
        ent_show_landing()
    elif stage == "quiz":
        ent_show_quiz()
    elif stage == "roles":
        ent_show_roles()
    elif stage == "simulation":
        ent_show_simulation()
    else:
        ent_show_landing()


# ============================================================
# PART 2 · Spark Discovery Hub (Identity + Confidence Labs)
# ============================================================

# ---- Spark Hub STATE ----

if "identity_raw" not in st.session_state:
    st.session_state.identity_raw = None

if "identity_result" not in st.session_state:
    st.session_state.identity_result = None

if "confidence_raw" not in st.session_state:
    st.session_state.confidence_raw = None

if "confidence_result" not in st.session_state:
    st.session_state.confidence_result = None


# ---- Spark Hub Bedrock Calls ----

def call_identity_ai(identity_data: dict):
    identity_json = json.dumps(identity_data, indent=2)

    prompt = f"""
You are a friendly creative-career mentor helping a young person in entertainment
discover their "Spark Identity".

You will receive:
1) Short quiz answers about how they behave and think.
2) Slider values for their "creative comfort zone".

Your job:
- Map them to 1–2 "Spark Archetypes" from this list:
  - Vision Architect
  - Vibe Curator
  - Story Weaver
  - Beat Builder
  - Humor Hacker
  - Detail Ninja
  - Bridge Builder

- Describe what kind of creative environment they’d thrive in
  (e.g., writer’s room, edit bay, dance crew, styling studio, social content lab).

- Suggest 3 entertainment-related roles that fit (practical, beginner-friendly).

Input data (user answers + sliders):

{identity_json}

Use the sliders as a 0–10 scale where:
- chaos_structure: 0 = loves chaos, 10 = loves structure
- solo_team: 0 = prefers solo, 10 = prefers team
- expression_observation: 0 = expressive, 10 = observer
- logic_emotion: 0 = logic-first, 10 = emotion-first
- people_backstage: 0 = very people-facing, 10 = fully backstage
- bigpicture_detail: 0 = big-picture, 10 = detail-focused

Return ONLY a single JSON object in this exact format (no extra text):

{{
  "spark_archetypes": [
    {{
      "name": "Vision Architect",
      "tagline": "You see the whole show before anyone presses record.",
      "description": "2–3 sentences in simple, encouraging language about why this archetype fits them."
    }}
  ],
  "creative_environment": {{
    "summary": "2–3 sentences describing where they thrive.",
    "example_spaces": [
      "Example creative space 1",
      "Example creative space 2"
    ]
  }},
  "suggested_roles": [
    {{
      "role_name": "Assistant Creative Producer",
      "why_it_fits": "1–2 sentences connecting this role to their archetype + comfort zone."
    }}
  ]
}}
"""

    try:
        raw = call_bedrock(prompt)
        data = safe_json_from_model(raw)

        if not isinstance(data, dict):
            raise ValueError("Identity AI output is not a JSON object.")

        return data

    except Exception as e:
        print("Identity Lab AI error:", repr(e))

        sliders = identity_data.get("sliders", {})
        chaos_val = sliders.get("chaos_structure", 5)
        solo_team = sliders.get("solo_team", 5)

        fallback_archetype = {
            "name": "Emerging Creator",
            "tagline": "You’re still exploring, but your creative spark is real.",
            "description": "Based on your answers, you enjoy playing with ideas and noticing details in your own way. This archetype means you don’t have to have it all figured out yet — you’re in the discovery phase, which is powerful."
        }

        if chaos_val >= 7:
            fallback_archetype["name"] = "Vibe Curator in Progress"
            fallback_archetype["tagline"] = "You like energy, mood, and letting things flow."
        elif chaos_val <= 3:
            fallback_archetype["name"] = "Vision Architect in Progress"
            fallback_archetype["tagline"] = "You like plans, structure, and knowing the why behind things."

        env_summary = (
            "You’d likely do well in a space that gives you room to learn, experiment, "
            "and contribute without all the pressure on you at once."
        )

        if solo_team >= 7:
            env_summary += " You seem to recharge around people and might enjoy small, tight-knit creative teams."
        elif solo_team <= 3:
            env_summary += " You might prefer roles where you can focus quietly and then share your work."

        return {
            "spark_archetypes": [fallback_archetype],
            "creative_environment": {
                "summary": env_summary,
                "example_spaces": [
                    "A small content studio where you can learn from others",
                    "A quiet edit bay or creator corner where you can focus"
                ],
            },
            "suggested_roles": [
                {
                    "role_name": "Content Assistant / Editor-in-training",
                    "why_it_fits": "You can experiment, learn tools, and slowly take on more responsibility without needing to be perfect on day one."
                },
                {
                    "role_name": "Production Helper on small shoots",
                    "why_it_fits": "You’ll see many parts of the process and figure out what you like best."
                },
            ],
        }


def call_confidence_ai(conf_data: dict):
    conf_json = json.dumps(conf_data, indent=2)

    prompt = f"""
You are a gentle but practical mentor for youth exploring entertainment careers.

Your task:
1) Take self-described "weaknesses" and reframe them into strengths that are useful in creative and entertainment work.
2) Look at concrete barriers (like money, time, no mentorship) and suggest small, low-cost actions they can take THIS WEEK.
3) End with a short encouragement paragraph that speaks directly to them.

Input data (weaknesses + barriers):

{conf_json}

Output format:
Return ONLY a single JSON object in this exact structure (no extra text):

{{
  "weakness_reframes": [
    {{
      "original": "I'm shy",
      "strength": "You’re thoughtful and observant, which makes you great at noticing details others miss.",
      "example_roles": ["Video editor", "Script researcher"],
      "encouragement": "You don’t have to be loud to be powerful — quiet focus is a creative superpower."
    }}
  ],
  "barrier_action_plan": [
    {{
      "barrier": "Money",
      "actions": [
        "List 3 free tools (like CapCut, Canva, DaVinci Resolve) you can try this week.",
        "Ask a friend if you can borrow a phone or device for 30 minutes to create a practice clip."
      ]
    }}
  ],
  "general_boost": "2–3 short sentences encouraging them, reminding them they are not behind, and that small steps count."
}}
"""

    try:
        raw = call_bedrock(prompt)
        data = safe_json_from_model(raw)

        if not isinstance(data, dict):
            raise ValueError("Confidence AI output is not a JSON object.")

        return data

    except Exception as e:
        print("Confidence Lab AI error:", repr(e))

        weaknesses = conf_data.get("weaknesses", [])
        barriers = conf_data.get("barriers", [])
        extra = conf_data.get("extra_barrier")

        # Simple fallback reframes
        reframes = []
        for w in weaknesses:
            strength = "You care deeply and notice things others might miss."
            roles = ["Content editor", "Research assistant for shows", "Behind-the-scenes coordinator"]
            if "shy" in w.lower():
                strength = "You’re observant and good at listening, which is powerful in backstage and editing roles."
                roles = ["Video editor", "Continuity checker", "Researcher"]
            elif "overthink" in w.lower():
                strength = "You think things through, which helps with planning and quality control."
                roles = ["Assistant producer", "Script reviewer", "Social media planner"]

            reframes.append(
                {
                    "original": w,
                    "strength": strength,
                    "example_roles": roles,
                    "encouragement": "Your way of being has value — you don’t need to become someone else to contribute creatively.",
                }
            )

        # Simple fallback actions
        all_barriers = barriers.copy()
        if extra:
            all_barriers.append(extra)

        action_plan = []
        for b in all_barriers:
            actions = [
                "Write down one tiny creative action you can do in 10 minutes this week.",
                "Find one free online resource (YouTube, TikTok, etc.) that teaches a skill you care about.",
            ]
            action_plan.append({"barrier": b, "actions": actions})

        general_boost = (
            "Even if things feel slow or blocked, every tiny experiment counts. You’re not behind — you’re just starting."
        )

        return {
            "weakness_reframes": reframes,
            "barrier_action_plan": action_plan,
            "general_boost": general_boost,
        }


def spark_main():
    # Header
    st.markdown(
        """
        <div style="text-align:center; padding: 16px 0 4px 0;">
            <div style="
                display:inline-block;
                padding: 6px 14px;
                border-radius: 999px;
                background: rgba(59,130,246,0.12);
                color: #60a5fa;
                font-size: 0.8rem;
                margin-bottom: 8px;
            ">
                Spark Discovery Hub · Usher's New Look
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.title("Spark Discovery Hub ✨")
    st.caption("Two quick labs to explore who you are creatively and how you can actually start.")

    tab1, tab2 = st.tabs(["🧪 Spark Identity Lab", "💪 Spark Confidence Lab"])

    # ---- TAB 1: Identity Lab ----
    with tab1:
        st.subheader("Spark Identity Lab")
        st.caption("Who are you creatively, and where do you thrive?")

        st.markdown("### Step 1 · Spark Archetype DNA")

        st.write("Answer a few fun questions. There are no wrong answers — just your flavor.")

        q1 = st.radio(
            "If you walk into a studio, what’s the **first** thing you’d do?",
            [
                "Grab the camera / mic and start experimenting",
                "Check the plan or schedule",
                "Talk to people, feel the vibe",
                "Find a quiet corner and observe",
            ],
            key="id_q1",
        )

        q2 = st.select_slider(
            "Pick your chaos level:",
            options=["📏 Super structured", "⚖️ Balanced", "🌪 Wild & chaotic"],
            key="id_q2",
        )

        q3 = st.radio(
            "When working with friends, you are usually the...",
            [
                "Idea person (always pitching concepts)",
                "Organizer (making sure things get done)",
                "Hype person (energy + support)",
                "Quiet observer (not loud, but noticing everything)",
            ],
            key="id_q3",
        )

        q4 = st.text_area(
            "Describe a moment when you felt proud of something creative you did (big or small):",
            key="id_q4",
            placeholder="Example: I edited a reel for a friend, choreographed a small dance, designed a flyer...",
        )

        q5 = st.radio(
            "What excites you more?",
            [
                "Starting new ideas and brainstorming",
                "Fixing / polishing something that’s almost there",
                "Helping people shine on camera or on stage",
                "Designing the mood, lighting, or overall aesthetic",
            ],
            key="id_q5",
        )

        q6 = st.text_input(
            "If you could shadow *any* creative person for a day, who would it be and why?",
            key="id_q6",
        )

        st.markdown("### Step 2 · Creative Comfort Zone Map")

        st.caption("Use the sliders — where do you naturally sit on these scales?")

        c1 = st.slider("Chaos  ↔  Structure", 0, 10, 5, key="id_c1")
        c2 = st.slider("Solo  ↔  Team", 0, 10, 5, key="id_c2")
        c3 = st.slider("Expression  ↔  Observation", 0, 10, 5, key="id_c3")
        c4 = st.slider("Logic  ↔  Emotion", 0, 10, 5, key="id_c4")
        c5 = st.slider("People-facing  ↔  Backstage", 0, 10, 5, key="id_c5")
        c6 = st.slider("Big Picture  ↔  Detail", 0, 10, 5, key="id_c6")

        if st.button("Reveal My Spark Identity 🔍", key="id_reveal"):
            identity_raw = {
                "answers": {
                    "q1": q1,
                    "q2": q2,
                    "q3": q3,
                    "q4": q4,
                    "q5": q5,
                    "q6": q6,
                },
                "sliders": {
                    "chaos_structure": c1,
                    "solo_team": c2,
                    "expression_observation": c3,
                    "logic_emotion": c4,
                    "people_backstage": c5,
                    "bigpicture_detail": c6,
                },
            }
            st.session_state.identity_raw = identity_raw

            with st.spinner("Reading your spark and building your archetype + environment…"):
                ai_result = call_identity_ai(identity_raw)

            st.session_state.identity_result = ai_result
            st.success("Spark Identity generated! Scroll down to see your results.")

        if st.session_state.identity_result:
            result = st.session_state.identity_result

            archetypes = result.get("spark_archetypes", [])
            env = result.get("creative_environment", {})
            roles = result.get("suggested_roles", [])

            st.markdown("---")
            st.markdown("## 🧬 Your Spark Archetype(s)")

            if not archetypes:
                st.info("We couldn’t detect specific archetypes this time, but your answers still matter.")
            else:
                for arch in archetypes:
                    name = arch.get("name", "Spark Archetype")
                    tagline = arch.get("tagline", "")
                    desc = arch.get("description", "")

                    card_html = f"""
                    <div style="
                        background: radial-gradient(circle at top left, #1f2937, #020617);
                        border-radius: 18px;
                        padding: 14px 16px;
                        margin-bottom: 12px;
                        box-shadow: 0 8px 20px rgba(0,0,0,0.35);
                        border: 1px solid rgba(148,163,184,0.5);
                    ">
                        <div style="font-size:0.8rem; opacity:0.8; margin-bottom:4px;">
                            Spark Archetype
                        </div>
                        <div style="font-size:1.1rem; font-weight:700; margin-bottom:4px;">
                            {name}
                        </div>
                        <div style="font-size:0.9rem; opacity:0.9; margin-bottom:4px;">
                            {tagline}
                        </div>
                        <div style="font-size:0.88rem; opacity:0.9;">
                            {desc}
                        </div>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)

            st.markdown("## 🌍 Your Ideal Creative Environment")

            env_summary = env.get("summary")
            env_spaces = env.get("example_spaces", [])

            if env_summary:
                st.write(env_summary)
            else:
                st.write(
                    "You’d likely thrive in a space that lets you experiment, learn, and contribute "
                    "without all the pressure on you at once."
                )

            if env_spaces:
                st.markdown("**Example spaces that might feel like home:**")
                st.markdown("- " + "\n- ".join(env_spaces))

            st.markdown("## 🎭 Suggested Entertainment Roles")

            if not roles:
                st.write(
                    "We don’t have specific roles listed yet, but any beginner-friendly assistant or creator role "
                    "near your interests is a great start."
                )
            else:
                for r in roles:
                    r_name = r.get("role_name", "Creative role")
                    r_why = r.get("why_it_fits", "")
                    st.markdown(f"**{r_name}**")
                    if r_why:
                        st.write(r_why)
                    st.markdown("---")

            with st.expander("See my raw answers (for coaches / mentors)"):
                st.json(st.session_state.identity_raw)

    # ---- TAB 2: Confidence Lab ----
    with tab2:
        st.subheader("Spark Confidence Lab")
        st.caption("Why you’re capable, and how to actually start.")

        st.markdown("### Step 1 · Weakness → Strength Transformer")

        weaknesses_text = st.text_area(
            "Type 3–5 things you *currently* see as weaknesses. One per line.",
            key="conf_weaknesses",
            placeholder="Example:\nI'm shy\nI overthink\nI get overwhelmed easily",
            height=120,
        )

        st.markdown("### Step 2 · Spark Barriers Breaker")

        barriers = st.multiselect(
            "What feels like it’s holding you back right now?",
            [
                "Money",
                "Time",
                "No mentorship",
                "No gear / equipment",
                "Skill gap (I don't know enough yet)",
                "Fear of judgment",
                "Not knowing where to start",
            ],
            key="conf_barriers",
        )

        extra_barrier = st.text_input(
            "Anything else you want to add as a barrier? (optional)",
            key="conf_extra_barrier",
            placeholder="Example: My family doesn’t understand creative careers...",
        )

        if st.button("Boost My Spark 🚀", key="conf_boost"):
            weakness_list = [
                w.strip()
                for w in weaknesses_text.split("\n")
                if w.strip()
            ]

            conf_raw = {
                "weaknesses": weakness_list,
                "barriers": barriers,
                "extra_barrier": extra_barrier.strip() or None,
            }
            st.session_state.confidence_raw = conf_raw

            if not weakness_list and not barriers and not extra_barrier.strip():
                st.warning("Share at least one weakness or one barrier so we can support you.")
            else:
                with st.spinner("Transforming your doubts into strengths + tiny action steps…"):
                    ai_result = call_confidence_ai(conf_raw)

                st.session_state.confidence_result = ai_result
                st.success("Spark Confidence boost ready! Scroll down to see your strengths and action plan.")

        if st.session_state.confidence_result:
            result = st.session_state.confidence_result

            reframes = result.get("weakness_reframes", [])
            plans = result.get("barrier_action_plan", [])
            boost = result.get("general_boost", "")

            st.markdown("---")
            st.markdown("## ✨ Weakness → Strength Transformer")

            if not reframes:
                st.info(
                    "No specific weaknesses were reframed this time, but the fact you’re reflecting is already a strength."
                )
            else:
                for item in reframes:
                    original = item.get("original", "")
                    strength = item.get("strength", "")
                    roles = item.get("example_roles", [])
                    encouragement = item.get("encouragement", "")

                    st.markdown(f"**Original:** {original}")
                    st.markdown(f"**Reframed strength:** {strength}")
                    if roles:
                        st.markdown("**Roles that could benefit from this:**")
                        st.markdown("- " + "\n- ".join(roles))
                    if encouragement:
                        st.markdown(f"_Note: {encouragement}_")
                    st.markdown("---")

            st.markdown("## 🚀 Your Barrier Breaker Action Plan")

            if not plans:
                st.write("No specific barriers were listed, but you can still choose one tiny step to try this week.")
            else:
                for p in plans:
                    barrier = p.get("barrier", "Barrier")
                    actions = p.get("actions", [])

                    st.markdown(f"**Barrier:** {barrier}")
                    if actions:
                        st.markdown("**Tiny steps you can try this week:**")
                        st.markdown("- " + "\n- ".join(actions))
                    st.markdown("---")

            if boost:
                st.markdown("## 💖 A Note for You")
                st.write(boost)

            with st.expander("See what you shared (for your own reflection)"):
                st.json(st.session_state.confidence_raw)


# ============================================================
# GLOBAL NAV (used only if you run entxp.py directly)
# ============================================================

def main():
    with st.sidebar:
        st.markdown("### 🔀 Navigate")
        page = st.radio(
            "Choose a space:",
            ["🎬 ENT.XP – Day Experience", "✨ Spark Discovery Hub"],
            key="global_nav",
        )

    if page.startswith("🎬"):
        ent_main()
    else:
        spark_main()


if __name__ == "__main__":
    main()
