```python
import streamlit as st
import streamlit.components.v1 as components
import time
import random
import string
import base64
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="OBE Level-Up", page_icon="🏗️", layout="wide")

LEVELS = ["IDENTIFY", "DEFINE", "DESIGN", "ALIGN", "REFINE"]

# One color per level — used for the projector pyramid bricks
LEVEL_COLORS = ["#4C6EF5", "#15AABF", "#40C057", "#F59F00", "#F03E3E"]

# Simple, neutral phonetic-alphabet labels -- unrelated to any level name
# (IDENTIFY, DEFINE, DESIGN, ALIGN, REFINE) or in-game vocabulary (OUTCOME,
# RUBRIC, ALIGNMENT) so they're never confused on the projector. Teams can
# rename themselves on the join screen if they prefer something else.
DEFAULT_TEAM_NAMES = {
    1: "Team Alpha",
    2: "Team Bravo",
    3: "Team Charlie",
    4: "Team Delta",
    5: "Team Echo",
}

QUESTIONS = {
    1: {
        "title": "🧩 LEVEL 1 — SORT THE EVIDENCE",
        "text": "Students can recall information but struggle to apply what they have learned to unfamiliar situations. What is the central learning need?",
        "options": [
            "Students need more information.",
            "Students need to memorize more content.",
            "Students need to apply learning independently in unfamiliar situations.",
            "Students need longer lectures."
        ],
        "answer": 2
    },
    2: {
        "title": "🔎 LEVEL 2 — THE CASE FILE",
        "text": "CASE: Students can recall the key features of a concept, but when given an unfamiliar situation, most cannot use the concept independently. Which outcome best addresses the learning need?",
        "options": [
            "Students will understand the concept.",
            "Students will learn the key features of the concept.",
            "Students will identify the main features of the concept.",
            "Students will apply the concept to an unfamiliar situation independently."
        ],
        "answer": 3
    },
    3: {
        "title": "🏗️ LEVEL 3 — BUILD THE LEARNING EXPERIENCE",
        "text": "Arrange the learning experience from teacher support toward independent performance.",
        "options": [
            "Teacher explanation",
            "Worked example",
            "Guided practice",
            "Independent application",
            "Reflection"
        ],
        "answer": [
            "Teacher explanation",
            "Worked example",
            "Guided practice",
            "Independent application",
            "Reflection"
        ]
    },
    4: {
        "title": "🚨 LEVEL 4 — FIND THE BREAK",
        "text": "OUTCOME: Students will apply a concept to an unfamiliar situation independently. ACTIVITY: Students work through increasingly unfamiliar examples with decreasing teacher support. ASSESSMENT: Students select the correct definition of the concept from four options. Where does alignment break?",
        "options": [
            "Outcome",
            "Learning activity",
            "Assessment",
            "Nothing — all three are aligned."
        ],
        "answer": 2
    }
}

# Level 5 is a word-search grid. Each word has a fixed start cell and
# direction so it's placed on the board without colliding with the others.
WORD_SEARCH_SIZE = 10
WORD_SEARCH_WORDS = [
    {
        "answer": "ALIGNMENT",
        "clue": "When the outcome, the learning activity, and the assessment all point to the same goal.",
        "start": (0, 0),
        "dir": (0, 1),
    },
    {
        "answer": "OUTCOME",
        "clue": "The intended result of learning, stated as what a student will be able to do.",
        "start": (0, 9),
        "dir": (1, 0),
    },
    {
        "answer": "RUBRIC",
        "clue": "A scoring guide that spells out the criteria used to judge performance.",
        "start": (2, 0),
        "dir": (1, 1),
    },
]


def build_word_search_grid():
    grid = [[None] * WORD_SEARCH_SIZE for _ in range(WORD_SEARCH_SIZE)]

    for w in WORD_SEARCH_WORDS:
        r, c = w["start"]
        dr, dc = w["dir"]

        for ch in w["answer"]:
            grid[r][c] = ch
            r += dr
            c += dc

    for r in range(WORD_SEARCH_SIZE):
        for c in range(WORD_SEARCH_SIZE):
            if grid[r][c] is None:
                grid[r][c] = random.choice(string.ascii_uppercase)

    return grid


@st.cache_resource
def get_shared_teams():
    """A single dict shared by EVERY browser session connected to this app.
    st.session_state is per-device, so team progress typed on a student's
    phone would never reach the presenter's screen. st.cache_resource with
    no arguments returns the exact same object to every session, so mutating
    it here updates it everywhere -- this is what makes the game 'live'."""
    return {
        i: {
            "level": 1,
            "score": 0,
            "completed": [False] * 5,
            "name": DEFAULT_TEAM_NAMES[i],
            "celebrated_team": False,
            "celebrated_presenter": False,
        }
        for i in range(1, 6)
    }


teams = get_shared_teams()

if "page" not in st.session_state:
    st.session_state.page = "home"

if "team" not in st.session_state:
    st.session_state.team = None


def pyramid(level):
    """Render a projector-friendly pyramid using colored HTML bricks
    instead of monospace block characters."""
    widths = [30, 45, 60, 75, 90]
    rows = []

    # Build top-to-bottom so it visually looks like a pyramid
    for i in range(4, -1, -1):
        completed = i < level
        color = LEVEL_COLORS[i] if completed else "#E9ECEF"
        text_color = "#FFFFFF" if completed else "#ADB5BD"
        label = LEVELS[i] if completed else "🔒"

        rows.append(
            f'''
            <div style="
                width:{widths[i]}%;
                margin:3px auto;
                background:{color};
                color:{text_color};
                text-align:center;
                border-radius:6px;
                padding:6px 0;
                font-family:sans-serif;
                font-weight:700;
                font-size:15px;
                letter-spacing:1px;
                box-shadow:0 2px 4px rgba(0,0,0,0.15);
            ">{label}</div>
            '''
        )

    return "".join(rows)


def celebrate(label):
    """Confetti burst, generated entirely in the browser."""
    components.html(
        f"""
        <script src="https://cdnjs.cloudflare.com/ajax/libs/canvas-confetti/1.9.2/confetti.browser.min.js"></script>
        <div style="text-align:center;font-family:sans-serif;font-weight:800;
                    font-size:22px;color:#F03E3E;padding-top:10px;">
            🎉 {label} 🎉
        </div>
        <script>
        (function() {{
            function fireConfetti() {{
                if (typeof confetti === 'function') {{
                    confetti({{particleCount:150, spread:90, origin:{{y:0.4}}}});
                    confetti({{particleCount:100, spread:130, origin:{{y:0.2}}}});
                    setTimeout(function() {{
                        confetti({{particleCount:80, spread:100, origin:{{y:0.5}}}});
                    }}, 300);
                }} else {{
                    setTimeout(fireConfetti, 100);
                }}
            }}
            fireConfetti();
        }})();
        </script>
        """,
        height=90,
    )


def play_level_sound():
    """Play the custom level-completion sound ONLY in the team's browser."""
    with open("level_complete.mp3", "rb") as audio_file:
        audio_bytes = audio_file.read()

    audio_base64 = base64.b64encode(audio_bytes).decode()

    components.html(
        f"""
        <audio id="levelSound" autoplay>
            <source src="data:audio/mpeg;base64,{audio_base64}" type="audio/mpeg">
        </audio>

        <script>
        (function() {{
            const audio = document.getElementById("levelSound");
            audio.volume = 1.0;

            function playSound() {{
                audio.play().catch(function(error) {{
                    console.log("Audio playback was blocked:", error);
                }});
            }}

            playSound();
        }})();
        </script>
        """,
        height=1,
    )


def advance(team_id, level):
    t = teams[team_id]
    t["completed"][level - 1] = True
    t["level"] = level + 1
    t["score"] += 100


def home():
    st.markdown(
        "<h1 style='text-align:center;font-size:52px;'>🏗️ OBE LEVEL-UP</h1>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<h3 style='text-align:center;color:#666;'>Build the Pyramid. Align the Learning.</h3>",
        unsafe_allow_html=True
    )

    st.write("")

    st.info(
        "Five teams. Five challenges. Complete each level to build your OBE pyramid."
    )

    a, b = st.columns(2)

    with a:
        if st.button(
            "👥 JOIN AS TEAM",
            use_container_width=True,
            type="primary"
        ):
            st.session_state.page = "join"
            st.rerun()

    with b:
        if st.button(
            "📺 PRESENTER DASHBOARD",
            use_container_width=True
        ):
            st.session_state.page = "presenter"
            st.rerun()


def join():
    st.title("👥 Join OBE Level-Up")

    team = st.selectbox(
        "Select your team",
        [t["name"] for t in teams.values()]
    )

    team_id = next(
        i for i, tm in teams.items()
        if tm["name"] == team
    )

    t = teams[team_id]

    if t["level"] > 5:
        st.info(
            f"**{t['name']}** has completed all levels! 🏆"
        )
    else:
        st.info(
            f"**{t['name']}** is currently on Level {t['level']}."
        )

    if st.button(
        "ENTER GAME",
        type="primary",
        use_container_width=True
    ):
        st.session_state.team = team_id
        st.session_state.page = "team"
        st.rerun()

    if st.button("← Back"):
        st.session_state.page = "home"
        st.rerun()


def team_game():
    team_id = st.session_state.team
    t = teams[team_id]
    level = t["level"]

    st.title(f"🏗️ {t['name']}")
    st.caption(f"Team {team_id}")

    if level > 5:
        st.success(
            "🏆 OBE MASTER — YOUR PYRAMID IS COMPLETE!"
        )

        st.markdown(
            pyramid(5),
            unsafe_allow_html=True
        )

        if not t["celebrated_team"]:
            celebrate(
                f"{t['name']} finished the pyramid!"
            )
            t["celebrated_team"] = True

        return

    st.progress((level - 1) / 5)

    if level == 5:
        st.subheader("🔁 LEVEL 5 — REFINE THE LOOP")
        st.write(
            "Find all 3 hidden words in the grid. Click letters to select them, then press Submit Word."
        )
    else:
        st.subheader(QUESTIONS[level]["title"])
        st.write(QUESTIONS[level]["text"])

    if level in [1, 2, 4]:

        options = QUESTIONS[level]["options"]

        order_key = f"order_{team_id}_{level}"

        if order_key not in st.session_state:
            order = list(range(len(options)))
            random.shuffle(order)
            st.session_state[order_key] = order

        order = st.session_state[order_key]

        choice_pos = st.radio(
            "Choose your team's response:",
            range(len(order)),
            format_func=lambda x: options[order[x]],
            key=f"q_{team_id}_{level}"
        )

        if st.button(
            "SUBMIT CHALLENGE",
            type="primary",
            use_container_width=True
        ):

            actual_choice = order[choice_pos]

            if actual_choice == QUESTIONS[level]["answer"]:

                advance(team_id, level)

                # SOUND PLAYS ONLY ON THIS TEAM'S DEVICE
                play_level_sound()

                st.session_state.pop(order_key, None)

                st.success(
                    f"🎉 Level {level} complete! Level {level + 1} unlocked."
                )

                # Give the browser time to start the audio
                time.sleep(1.5)

                st.rerun()

            else:
                st.error(
                    "Not quite. Discuss it and try again."
                )

    elif level == 3:

        st.write(
            "Select the blocks in the order your team recommends."
        )

        pool_key = f"pool_{team_id}_3"

        if pool_key not in st.session_state:
            pool = QUESTIONS[3]["options"][:]
            random.shuffle(pool)
            st.session_state[pool_key] = pool

        pool = st.session_state[pool_key]

        selected = st.multiselect(
            "Build your sequence:",
            pool,
            key=f"q_{team_id}_3"
        )

        if st.button(
            "SUBMIT SEQUENCE",
            type="primary",
            use_container_width=True
        ):

            if selected == QUESTIONS[3]["answer"]:

                advance(team_id, 3)

                # SOUND PLAYS ONLY ON THIS TEAM'S DEVICE
                play_level_sound()

                st.session_state.pop(pool_key, None)

                st.success(
                    "🎉 Level 3 complete! Level 4 unlocked."
                )

                # Give the browser time to start the audio
                time.sleep(1.5)

                st.rerun()

            else:
                st.error(
                    "Reconsider the movement from support toward independence."
                )

    elif level == 5:

        grid_key = f"l5_grid_{team_id}"
        sel_key = f"l5_selected_{team_id}"
        found_key = f"l5_found_{team_id}"

        if grid_key not in st.session_state:
            st.session_state[grid_key] = build_word_search_grid()

        if sel_key not in st.session_state:
            st.session_state[sel_key] = []

        if found_key not in st.session_state:
            st.session_state[found_key] = set()

        grid = st.session_state[grid_key]
        selected = st.session_state[sel_key]
        found = st.session_state[found_key]

        grid_col, clue_col = st.columns([3, 2])

        with grid_col:

            for r in range(WORD_SEARCH_SIZE):

                row_cells = st.columns(
                    WORD_SEARCH_SIZE,
                    gap="small"
                )

                for c in range(WORD_SEARCH_SIZE):

                    letter = grid[r][c]
                    is_selected = (r, c) in selected

                    btn_type = (
                        "primary"
                        if is_selected
                        else "secondary"
                    )

                    if row_cells[c].button(
                        letter,
                        key=f"cell_{team_id}_{r}_{c}",
                        type=btn_type,
                        use_container_width=True
                    ):

                        if is_selected:
                            selected.remove((r, c))
                        else:
                            selected.append((r, c))

                        st.rerun()

        with clue_col:

            st.markdown("**Clues**")

            for w in WORD_SEARCH_WORDS:

                icon = (
                    "✅"
                    if w["answer"] in found
                    else "🔲"
                )

                st.markdown(
                    f"{icon} {w['clue']} *({len(w['answer'])} letters)*"
                )

            current_word = "".join(
                grid[r][c]
                for r, c in selected
            )

            st.text_input(
                "Selected letters",
                value=current_word,
                disabled=True
            )

            b1, b2 = st.columns(2)

            if b1.button(
                "Clear",
                use_container_width=True
            ):
                st.session_state[sel_key] = []
                st.rerun()

            if b2.button(
                "Submit Word",
                type="primary",
                use_container_width=True
            ):

                match = None

                for w in WORD_SEARCH_WORDS:

                    if w["answer"] in found:
                        continue

                    if current_word in (
                        w["answer"],
                        w["answer"][::-1]
                    ):
                        match = w["answer"]
                        break

                if match:

                    found.add(match)
                    st.session_state[sel_key] = []

                    if len(found) == len(WORD_SEARCH_WORDS):

                        advance(team_id, 5)

                        # SOUND PLAYS ONLY ON THIS TEAM'S DEVICE
                        play_level_sound()

                        st.success(
                            "🎉 All words found! Pyramid finished!"
                        )

                        # Give the browser time to start the audio
                        time.sleep(1.5)

                    else:

                        st.success(
                            f"✅ Found: {match}!"
                        )

                    st.rerun()

                else:

                    st.error(
                        "Not one of the target words — try again."
                    )

                    st.session_state[sel_key] = []
                    st.rerun()


def presenter():

    # Silently reruns this page every 2 seconds so scores/pyramids update
    # on the projector without anyone clicking Refresh.
    st_autorefresh(
        interval=2000,
        key="presenter_autorefresh"
    )

    # Tighten Streamlit's default padding/margins so the whole dashboard
    # fits on one screen without scrolling on a typical projector/TV.
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 0.5rem;
        }
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.3rem;
        }
        hr { margin: 0.6rem 0; }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        "<h2 style='text-align:center;margin-bottom:0;'>📺 OBE LEVEL-UP — LIVE DASHBOARD</h2>",
        unsafe_allow_html=True
    )

    cols = st.columns(5)

    for i, col in enumerate(cols, start=1):

        t = teams[i]
        level = min(t["level"], 5)
        done = sum(t["completed"])

        just_finished = (
            t["level"] > 5
            and not t["celebrated_presenter"]
        )

        with col:

            st.markdown(
                f"<h4 style='text-align:center;margin:0;' "
                f"title='Team {i}'>{t['name']}</h4>",
                unsafe_allow_html=True
            )

            status = (
                "🏆 COMPLETE"
                if t["level"] > 5
                else f"LEVEL {t['level']}"
            )

            st.markdown(
                f"<div style='text-align:center;font-size:18px;font-weight:800;"
                f"color:{'#F03E3E' if t['level']>5 else '#212529'};margin-bottom:2px;'>"
                f"{status}</div>",
                unsafe_allow_html=True
            )

            st.markdown(
                pyramid(level),
                unsafe_allow_html=True
            )

            st.progress(done / 5)

            st.markdown(
                f"<div style='text-align:center;font-size:13px;color:#666;margin-top:2px;'>"
                f"{done}/5 levels • {t['score']} pts</div>",
                unsafe_allow_html=True
            )

            if just_finished:

                celebrate(
                    f"{t['name']} finished the pyramid!"
                )

                t["celebrated_presenter"] = True

    st.divider()

    # ---- Level-by-level progress grid, shown directly ----
    st.markdown(
        "<h4 style='margin:0.2rem 0;'>📋 Level-by-Level Progress</h4>",
        unsafe_allow_html=True
    )

    header = st.columns(6)

    header[0].markdown("**TEAM**")

    for i, name in enumerate(LEVELS, start=1):
        header[i].markdown(
            f"**{i}. {name}**"
        )

    for i in range(1, 6):

        t = teams[i]
        row = st.columns(6)

        row[0].markdown(
            f"**{t['name']}**"
        )

        for j in range(5):

            done = t["completed"][j]

            color = (
                LEVEL_COLORS[j]
                if done
                else "#E9ECEF"
            )

            text = "✓" if done else ""

            row[j + 1].markdown(
                f"<div style='background:{color};border-radius:6px;height:28px;"
                f"display:flex;align-items:center;justify-content:center;"
                f"color:white;font-weight:700;font-size:13px;'>{text}</div>",
                unsafe_allow_html=True
            )

    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "🔄 Refresh Dashboard",
            use_container_width=True
        ):
            st.rerun()

    with c2:
        if st.button(
            "🏠 Home",
            use_container_width=True
        ):
            st.session_state.page = "home"
            st.rerun()


def demo():

    st.title("⚙️ Demo Control")

    st.caption(
        "Use this to test the presenter screen before the real multiplayer version."
    )

    for i in range(1, 6):

        t = teams[i]
        c1, c2 = st.columns([2, 1])

        status = (
            "COMPLETE"
            if t["level"] > 5
            else f"Level {t['level']}"
        )

        c1.write(
            f"**{t['name']}** (Team {i}) — {status}"
        )

        if c2.button(
            f"Advance Team {i}",
            key=f"advance_{i}"
        ):

            if t["level"] <= 5:
                advance(i, t["level"])

            st.rerun()

    if st.button("Reset All Teams"):

        for i in range(1, 6):

            teams[i]["level"] = 1
            teams[i]["score"] = 0
            teams[i]["completed"] = [False] * 5
            teams[i]["name"] = DEFAULT_TEAM_NAMES[i]
            teams[i]["celebrated_team"] = False
            teams[i]["celebrated_presenter"] = False

            st.session_state.pop(
                f"l5_grid_{i}",
                None
            )

            st.session_state.pop(
                f"l5_selected_{i}",
                None
            )

            st.session_state.pop(
                f"l5_found_{i}",
                None
            )

        st.rerun()

    if st.button("← Home"):
        st.session_state.page = "home"
        st.rerun()


if st.session_state.page == "home":
    home()

elif st.session_state.page == "join":
    join()

elif st.session_state.page == "team":
    team_game()

elif st.session_state.page == "presenter":
    presenter()

elif st.session_state.page == "demo":
    demo()
```
