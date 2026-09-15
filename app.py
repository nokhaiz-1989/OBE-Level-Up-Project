import streamlit as st
import streamlit.components.v1 as components
import time
import random
import string
import base64
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="OBE Level-Up", page_icon="🏗️", layout="wide")

LEVELS = ["IDENTIFY", "DEFINE", "DESIGN", "ALIGN", "REFINE"]

# What the team has actually *done* by clearing each level. Shown as a
# running checklist so the game reads as one OBE design process rather than
# five unrelated puzzles. Index 0 = Level 1.
OBE_STEPS = [
    "Identified the learning need",
    "Defined the learning outcome",
    "Designed the learning activity",
    "Aligned the assessment with the activity",
    "Refined the loop as a teacher",
]

# One color per level — used for the projector pyramid bricks
LEVEL_COLORS = ["#4C6EF5", "#15AABF", "#40C057", "#F59F00", "#F03E3E"]

# ---- Economy -------------------------------------------------------------
# Every team starts the session with the same wallet. A wrong answer costs
# coins; finishing a level pays coins back. Tune these three numbers to
# change how punishing / generous the game feels.
START_COINS = 100
WRONG_PENALTY = 10
LEVEL_REWARD = 25

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
    6: "Team Fifa",
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
            "coins": START_COINS,
            "misses": 0,
            "completed": [False] * 5,
            "name": DEFAULT_TEAM_NAMES[i],
            "celebrated_team": False,
            "celebrated_presenter": False,
        }
        for i in range(1, 7)
    }


teams = get_shared_teams()

if "page" not in st.session_state:
    st.session_state.page = "home"

if "team" not in st.session_state:
    st.session_state.team = None


# --------------------------------------------------------------------------
# Styling
# --------------------------------------------------------------------------
def inject_game_css():
    """Arcade-style skin for the team screens: heavy type, chunky answer
    tiles, and a scoped size bump so the word-search cells stay small while
    the answer tiles get large. Scoping relies on Streamlit's per-widget
    `st-key-<key>` class (Streamlit >= 1.39); on older versions the rules are
    simply ignored and the app still works."""

    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; max-width: 1150px; }

        /* ---------- HUD ---------- */
        .hud {
            display:flex; align-items:center; justify-content:space-between;
            gap:14px; flex-wrap:wrap;
            background:#101534;
            border:2px solid #2B3566;
            border-radius:16px;
            padding:14px 22px;
            margin-bottom:18px;
        }
        .hud-team {
            font-family:'Trebuchet MS', sans-serif;
            font-size:30px; font-weight:800; color:#FFFFFF; line-height:1.1;
        }
        .hud-sub { font-size:15px; color:#98A2D8; margin-top:2px; }
        .hud-stat {
            background:#1B2350; border-radius:12px; padding:8px 18px;
            text-align:center; min-width:120px;
        }
        .hud-stat .val {
            font-size:30px; font-weight:800; color:#FFD43B; line-height:1.1;
        }
        .hud-stat .lbl {
            font-size:12px; letter-spacing:1.5px; color:#98A2D8; margin-top:2px;
        }
        .hud-stat.level .val { color:#63E6BE; }

        /* ---------- Question card ---------- */
        .qcard {
            background:#FFFFFF;
            border:3px solid #101534;
            border-radius:18px;
            padding:26px 30px;
            box-shadow:0 8px 0 #101534;
            margin-bottom:22px;
        }
        .qcard .qtitle {
            font-family:'Trebuchet MS', sans-serif;
            font-size:30px; font-weight:800; color:#101534; margin-bottom:12px;
        }
        .qcard .qtext {
            font-size:23px; line-height:1.55; color:#1F2544;
        }
        .qhint {
            font-size:18px; color:#4A5280; margin:4px 0 14px 0; font-weight:600;
        }

        /* ---------- Big answer tiles ---------- */
        div[class*="st-key-opt_"] button,
        div[class*="st-key-seq_"] button,
        div[class*="st-key-submit_"] button {
            font-size:22px !important;
            font-weight:700 !important;
            line-height:1.4 !important;
            padding:20px 22px !important;
            border-radius:14px !important;
            border:3px solid #101534 !important;
            text-align:left !important;
            white-space:normal !important;
            height:auto !important;
            box-shadow:0 5px 0 #101534 !important;
            transition:transform .06s ease-in-out !important;
        }
        div[class*="st-key-opt_"] button:hover,
        div[class*="st-key-seq_"] button:hover,
        div[class*="st-key-submit_"] button:hover {
            transform:translateY(2px);
            box-shadow:0 3px 0 #101534 !important;
            border-color:#101534 !important;
        }
        div[class*="st-key-submit_"] button { text-align:center !important; }

        /* ---------- Word-search cells stay compact ---------- */
        div[class*="st-key-cell_"] button {
            font-size:20px !important;
            font-weight:800 !important;
            padding:6px 0 !important;
            border-radius:8px !important;
            min-height:46px !important;
        }

        /* ---------- OBE step checklist ---------- */
        .steps {
            background:#F6F7FC;
            border:2px solid #D7DBEF;
            border-radius:16px;
            padding:16px 20px;
            margin-bottom:20px;
        }
        .steps-head {
            font-family:'Trebuchet MS', sans-serif;
            font-size:19px; font-weight:800; color:#101534; margin-bottom:10px;
        }
        .step {
            display:flex; align-items:center; gap:12px;
            font-size:19px; line-height:1.45;
            padding:7px 10px; border-radius:10px; margin-bottom:4px;
        }
        .step .num {
            width:30px; height:30px; flex:none; border-radius:50%;
            display:flex; align-items:center; justify-content:center;
            font-size:15px; font-weight:800; color:#FFFFFF;
        }
        .step.done { color:#1F2544; font-weight:700; background:#EDFBF0; }
        .step.now  { color:#101534; font-weight:700; background:#FFF8E1;
                     box-shadow:inset 0 0 0 2px #F59F00; }
        .step.todo { color:#8A90AE; }
        .step .tag { margin-left:auto; font-size:15px; font-weight:700; }

        .seqchip {
            display:inline-block; background:#101534; color:#FFFFFF;
            font-size:19px; font-weight:700;
            border-radius:10px; padding:8px 14px; margin:4px 6px 4px 0;
        }
        .seqempty {
            font-size:19px; color:#7A83A8; font-style:italic; padding:8px 0;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


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


def hud(t):
    """Team name, current level and coin wallet, always on screen."""
    level_label = "DONE" if t["level"] > 5 else f"{t['level']} / 5"

    st.markdown(
        f"""
        <div class="hud">
            <div>
                <div class="hud-team">🏗️ {t['name']}</div>
                <div class="hud-sub">{t['misses']} wrong attempt(s) so far</div>
            </div>
            <div style="display:flex;gap:12px;">
                <div class="hud-stat level">
                    <div class="val">{level_label}</div>
                    <div class="lbl">LEVEL</div>
                </div>
                <div class="hud-stat">
                    <div class="val">🪙 {t['coins']}</div>
                    <div class="lbl">COINS</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def steps_html(t):
    """The five OBE moves, ticked off as the team clears each level."""
    rows = []

    for i, step in enumerate(OBE_STEPS):

        done = t["completed"][i]
        current = (not done) and (t["level"] == i + 1)

        if done:
            state, badge, tag = "done", "✓", "done"
        elif current:
            state, badge, tag = "now", str(i + 1), "you are here"
        else:
            state, badge, tag = "todo", "🔒", ""

        bg = LEVEL_COLORS[i] if done else ("#F59F00" if current else "#C6CADB")

        rows.append(
            f"<div class='step {state}'>"
            f"<span class='num' style='background:{bg};'>{badge}</span>"
            f"<span>{i + 1}. {step}</span>"
            f"<span class='tag'>{tag}</span>"
            f"</div>"
        )

    cleared = sum(t["completed"])

    return (
        "<div class='steps'>"
        f"<div class='steps-head'>Your OBE design so far — {cleared} of 5 complete</div>"
        + "".join(rows) +
        "</div>"
    )


def correct_popup(message, reward):
    """Green tick that pops in, plus a confetti burst and the coin gain."""
    components.html(
        f"""
        <script src="https://cdnjs.cloudflare.com/ajax/libs/canvas-confetti/1.9.2/confetti.browser.min.js"></script>
        <style>
        .pop-wrap {{
            font-family:'Trebuchet MS', sans-serif;
            text-align:center; padding-top:6px;
        }}
        .pop-tick {{
            width:110px; height:110px; margin:0 auto;
            border-radius:50%;
            background:#40C057;
            color:#FFFFFF; font-size:62px; font-weight:800;
            display:flex; align-items:center; justify-content:center;
            box-shadow:0 0 0 10px rgba(64,192,87,0.25);
            animation:pop .45s cubic-bezier(.17,.89,.32,1.49);
        }}
        .pop-msg {{
            font-size:26px; font-weight:800; color:#2B8A3E; margin-top:12px;
        }}
        .pop-coins {{
            font-size:22px; font-weight:700; color:#B08900; margin-top:4px;
            animation:rise .7s ease-out;
        }}
        @keyframes pop {{
            0%   {{ transform:scale(0);   opacity:0; }}
            60%  {{ transform:scale(1.18); opacity:1; }}
            100% {{ transform:scale(1); }}
        }}
        @keyframes rise {{
            0%   {{ transform:translateY(14px); opacity:0; }}
            100% {{ transform:translateY(0);    opacity:1; }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            .pop-tick, .pop-coins {{ animation:none; }}
        }}
        </style>

        <div class="pop-wrap">
            <div class="pop-tick">✓</div>
            <div class="pop-msg">{message}</div>
            <div class="pop-coins">+{reward} coins</div>
        </div>

        <script>
        (function() {{
            function fire() {{
                if (typeof confetti === 'function') {{
                    confetti({{particleCount:150, spread:90, origin:{{y:0.4}}}});
                    confetti({{particleCount:100, spread:130, origin:{{y:0.2}}}});
                    setTimeout(function() {{
                        confetti({{particleCount:80, spread:100, origin:{{y:0.5}}}});
                    }}, 300);
                }} else {{
                    setTimeout(fire, 100);
                }}
            }}
            fire();
        }})();
        </script>
        """,
        height=260,
    )


def penalty_popup(message, penalty, coins_left):
    """Red cross with the coins floating away — shown after a wrong answer."""
    components.html(
        f"""
        <style>
        .miss-wrap {{
            font-family:'Trebuchet MS', sans-serif;
            display:flex; align-items:center; gap:18px;
            background:#FFF5F5; border:3px solid #F03E3E;
            border-radius:16px; padding:16px 22px;
            animation:shake .4s ease-in-out;
        }}
        .miss-x {{
            width:64px; height:64px; flex:none; border-radius:50%;
            background:#F03E3E; color:#FFFFFF;
            font-size:34px; font-weight:800;
            display:flex; align-items:center; justify-content:center;
        }}
        .miss-msg {{ font-size:22px; font-weight:700; color:#C92A2A; }}
        .miss-sub {{ font-size:17px; color:#862E2E; margin-top:3px; }}
        .miss-cost {{
            margin-left:auto; font-size:30px; font-weight:800; color:#F03E3E;
            animation:drift 1s ease-out;
        }}
        @keyframes shake {{
            0%,100% {{ transform:translateX(0); }}
            25%     {{ transform:translateX(-9px); }}
            75%     {{ transform:translateX(9px); }}
        }}
        @keyframes drift {{
            0%   {{ transform:translateY(0);    opacity:1; }}
            100% {{ transform:translateY(-10px); opacity:1; }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            .miss-wrap, .miss-cost {{ animation:none; }}
        }}
        </style>

        <div class="miss-wrap">
            <div class="miss-x">✕</div>
            <div>
                <div class="miss-msg">{message}</div>
                <div class="miss-sub">🪙 {coins_left} coins left in the wallet</div>
            </div>
            <div class="miss-cost">−{penalty}</div>
        </div>
        """,
        height=130,
    )


def play_level_sound():
    """Play the custom level-completion sound ONLY in the team's browser."""
    try:
        with open("level_complete.mp3", "rb") as audio_file:
            audio_bytes = audio_file.read()
    except FileNotFoundError:
        return

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
            audio.play().catch(function(error) {{
                console.log("Audio playback was blocked:", error);
            }});
        }})();
        </script>
        """,
        height=1,
    )


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------
def advance(team_id, level):
    t = teams[team_id]
    t["completed"][level - 1] = True
    t["level"] = level + 1
    t["score"] += 100
    t["coins"] += LEVEL_REWARD


def charge_miss(team_id, message):
    """Deduct coins for a wrong attempt and queue the penalty animation."""
    t = teams[team_id]
    t["misses"] += 1
    t["coins"] = max(0, t["coins"] - WRONG_PENALTY)

    st.session_state[f"flash_{team_id}"] = {
        "message": message,
        "penalty": WRONG_PENALTY,
        "coins": t["coins"],
    }


def show_flash(team_id):
    flash = st.session_state.pop(f"flash_{team_id}", None)

    if flash:
        penalty_popup(
            flash["message"],
            flash["penalty"],
            flash["coins"]
        )


def complete_level(team_id, level, message):
    """Shared success path: advance, pay out, celebrate, move on."""
    advance(team_id, level)

    correct_popup(message, LEVEL_REWARD)

    # SOUND PLAYS ONLY ON THIS TEAM'S DEVICE
    play_level_sound()

    # Let the animation and audio finish before the screen changes
    time.sleep(2.2)


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
def home():
    st.markdown(
        "<h1 style='text-align:center;font-size:62px;margin-bottom:0;'>🏗️ OBE LEVEL-UP</h1>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<h3 style='text-align:center;color:#666;font-weight:500;'>"
        "Build the pyramid. Align the learning.</h3>",
        unsafe_allow_html=True
    )

    st.write("")

    st.info(
        f"Six teams. Five challenges. Every team starts with {START_COINS} coins — "
        f"a wrong answer costs {WRONG_PENALTY}, and clearing a level pays {LEVEL_REWARD} back."
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
            f"**{t['name']}** has completed all levels! 🏆  •  🪙 {t['coins']} coins"
        )
    else:
        st.info(
            f"**{t['name']}** is on Level {t['level']}  •  🪙 {t['coins']} coins"
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
    inject_game_css()

    team_id = st.session_state.team
    t = teams[team_id]
    level = t["level"]

    hud(t)

    if level > 5:
        st.markdown(
            "<div class='qcard'><div class='qtitle'>🏆 OBE MASTER — YOUR PYRAMID IS COMPLETE</div>"
            f"<div class='qtext'>Final wallet: 🪙 {t['coins']} coins after "
            f"{t['misses']} wrong attempt(s).</div></div>",
            unsafe_allow_html=True
        )

        st.markdown(pyramid(5), unsafe_allow_html=True)

        if not t["celebrated_team"]:
            correct_popup(f"{t['name']} finished the pyramid!", LEVEL_REWARD)
            t["celebrated_team"] = True

        return

    st.progress((level - 1) / 5)

    show_flash(team_id)

    # ---- Question card ----
    if level == 5:
        st.markdown(
            "<div class='qcard'>"
            "<div class='qtitle'>🔁 LEVEL 5 — REFINE THE LOOP</div>"
            "<div class='qtext'>Three words are hidden in the grid. Tap letters to "
            "spell a word, then submit it. A wrong word costs coins.</div>"
            "</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div class='qcard'>"
            f"<div class='qtitle'>{QUESTIONS[level]['title']}</div>"
            f"<div class='qtext'>{QUESTIONS[level]['text']}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    # ---- Levels 1, 2, 4: tap an answer tile ----
    if level in [1, 2, 4]:

        options = QUESTIONS[level]["options"]
        order_key = f"order_{team_id}_{level}"

        if order_key not in st.session_state:
            order = list(range(len(options)))
            random.shuffle(order)
            st.session_state[order_key] = order

        order = st.session_state[order_key]

        st.markdown(
            f"<div class='qhint'>Tap your team's answer — a wrong tap costs "
            f"{WRONG_PENALTY} coins.</div>",
            unsafe_allow_html=True
        )

        for pos, idx in enumerate(order):

            label = f"{chr(65 + pos)}.  {options[idx]}"

            if st.button(
                label,
                key=f"opt_{team_id}_{level}_{pos}",
                use_container_width=True
            ):

                if idx == QUESTIONS[level]["answer"]:

                    st.session_state.pop(order_key, None)

                    complete_level(
                        team_id,
                        level,
                        f"Level {level} cleared — Level {level + 1} unlocked!"
                    )

                else:
                    charge_miss(
                        team_id,
                        "Not the one. Talk it over and pick again."
                    )

                st.rerun()

    # ---- Level 3: tap blocks in order ----
    elif level == 3:

        pool_key = f"pool_{team_id}_3"
        seq_key = f"seq_{team_id}_3"

        if pool_key not in st.session_state:
            pool = QUESTIONS[3]["options"][:]
            random.shuffle(pool)
            st.session_state[pool_key] = pool

        if seq_key not in st.session_state:
            st.session_state[seq_key] = []

        pool = st.session_state[pool_key]
        sequence = st.session_state[seq_key]

        st.markdown(
            "<div class='qhint'>Tap the blocks in the order your team recommends.</div>",
            unsafe_allow_html=True
        )

        if sequence:
            chips = "".join(
                f"<span class='seqchip'>{n}. {block}</span>"
                for n, block in enumerate(sequence, start=1)
            )
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.markdown(
                "<div class='seqempty'>Your sequence will build up here.</div>",
                unsafe_allow_html=True
            )

        left, right = st.columns(2)

        for n, block in enumerate(pool):

            used = block in sequence
            target = left if n % 2 == 0 else right

            if target.button(
                ("✔ " if used else "➕ ") + block,
                key=f"seq_{team_id}_3_{n}",
                use_container_width=True,
                disabled=used
            ):
                sequence.append(block)
                st.rerun()

        c1, c2 = st.columns(2)

        if c1.button(
            "↺ Clear sequence",
            key="submit_clear_3",
            use_container_width=True
        ):
            st.session_state[seq_key] = []
            st.rerun()

        if c2.button(
            "🚀 Lock in sequence",
            key="submit_seq_3",
            type="primary",
            use_container_width=True,
            disabled=len(sequence) < len(pool)
        ):

            if sequence == QUESTIONS[3]["answer"]:

                st.session_state.pop(pool_key, None)
                st.session_state.pop(seq_key, None)

                complete_level(
                    team_id,
                    3,
                    "Level 3 cleared — Level 4 unlocked!"
                )

            else:
                st.session_state[seq_key] = []

                charge_miss(
                    team_id,
                    "Not yet — move from teacher support toward independence."
                )

            st.rerun()

    # ---- Level 5: word search ----
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

                row_cells = st.columns(WORD_SEARCH_SIZE, gap="small")

                for c in range(WORD_SEARCH_SIZE):

                    letter = grid[r][c]
                    is_selected = (r, c) in selected

                    if row_cells[c].button(
                        letter,
                        key=f"cell_{team_id}_{r}_{c}",
                        type="primary" if is_selected else "secondary",
                        use_container_width=True
                    ):

                        if is_selected:
                            selected.remove((r, c))
                        else:
                            selected.append((r, c))

                        st.rerun()

        with clue_col:

            st.markdown("#### Clues")

            for w in WORD_SEARCH_WORDS:

                icon = "✅" if w["answer"] in found else "🔲"

                st.markdown(
                    f"<div style='font-size:19px;line-height:1.5;margin-bottom:8px;'>"
                    f"{icon} {w['clue']} <i>({len(w['answer'])} letters)</i></div>",
                    unsafe_allow_html=True
                )

            current_word = "".join(grid[r][c] for r, c in selected)

            st.markdown(
                f"<div style='font-size:30px;font-weight:800;letter-spacing:4px;"
                f"background:#101534;color:#FFD43B;border-radius:12px;"
                f"padding:12px;text-align:center;margin:10px 0;min-height:56px;'>"
                f"{current_word or '&nbsp;'}</div>",
                unsafe_allow_html=True
            )

            b1, b2 = st.columns(2)

            if b1.button(
                "↺ Clear",
                key="submit_clear_5",
                use_container_width=True
            ):
                st.session_state[sel_key] = []
                st.rerun()

            if b2.button(
                "🚀 Submit word",
                key="submit_word_5",
                type="primary",
                use_container_width=True,
                disabled=not current_word
            ):

                match = None

                for w in WORD_SEARCH_WORDS:

                    if w["answer"] in found:
                        continue

                    if current_word in (w["answer"], w["answer"][::-1]):
                        match = w["answer"]
                        break

                st.session_state[sel_key] = []

                if match:

                    found.add(match)

                    if len(found) == len(WORD_SEARCH_WORDS):
                        complete_level(
                            team_id,
                            5,
                            "All three words found — pyramid finished!"
                        )
                    else:
                        remaining = len(WORD_SEARCH_WORDS) - len(found)

                        st.markdown(
                            f"<div style='font-size:22px;font-weight:700;color:#2B8A3E;'>"
                            f"✅ {match} found — {remaining} to go.</div>",
                            unsafe_allow_html=True
                        )

                        time.sleep(1.2)

                else:
                    charge_miss(
                        team_id,
                        "That isn't one of the hidden words."
                    )

                st.rerun()

    st.write("")

    if st.button("← Leave game"):
        st.session_state.page = "home"
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

    cols = st.columns(6)

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
                f"<div style='text-align:center;font-size:24px;font-weight:800;"
                f"color:#B08900;margin-bottom:4px;'>🪙 {t['coins']}</div>",
                unsafe_allow_html=True
            )

            st.markdown(
                pyramid(level),
                unsafe_allow_html=True
            )

            st.progress(done / 5)

            st.markdown(
                f"<div style='text-align:center;font-size:13px;color:#666;margin-top:2px;'>"
                f"{done}/5 levels • {t['misses']} misses</div>",
                unsafe_allow_html=True
            )

            if just_finished:

                correct_popup(
                    f"{t['name']} finished the pyramid!",
                    LEVEL_REWARD
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

    for i in range(1, 7):

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

    for i in range(1, 7):

        t = teams[i]
        c1, c2 = st.columns([2, 1])

        status = (
            "COMPLETE"
            if t["level"] > 5
            else f"Level {t['level']}"
        )

        c1.write(
            f"**{t['name']}** (Team {i}) — {status} • 🪙 {t['coins']}"
        )

        if c2.button(
            f"Advance Team {i}",
            key=f"advance_{i}"
        ):

            if t["level"] <= 5:
                advance(i, t["level"])

            st.rerun()

    if st.button("Reset All Teams"):

        for i in range(1, 7):

            teams[i]["level"] = 1
            teams[i]["score"] = 0
            teams[i]["coins"] = START_COINS
            teams[i]["misses"] = 0
            teams[i]["completed"] = [False] * 5
            teams[i]["name"] = DEFAULT_TEAM_NAMES[i]
            teams[i]["celebrated_team"] = False
            teams[i]["celebrated_presenter"] = False

            for prefix in ("l5_grid_", "l5_selected_", "l5_found_",
                           "seq_", "pool_", "flash_"):
                st.session_state.pop(f"{prefix}{i}", None)

            st.session_state.pop(f"pool_{i}_3", None)
            st.session_state.pop(f"seq_{i}_3", None)

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
