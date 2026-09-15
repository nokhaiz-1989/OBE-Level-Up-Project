import streamlit as st
import streamlit.components.v1 as components
import time
import random
import string
import base64
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="OBE Level-Up", page_icon="🏗️", layout="wide")

LEVELS = ["IDENTIFY", "DEFINE", "DESIGN", "ALIGN", "REFINE"]

# One color per level — used for the pyramid bricks
LEVEL_COLORS = ["#4C6EF5", "#15AABF", "#40C057", "#F59F00", "#F03E3E"]

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

# ---- Economy -------------------------------------------------------------
# Every team starts the session with the same wallet. A wrong answer costs
# coins; finishing a level pays coins back. Tune these three numbers to
# change how punishing / generous the game feels.
START_COINS = 100
WRONG_PENALTY = 10
LEVEL_REWARD = 25

# Simple, neutral phonetic-alphabet labels -- unrelated to any level name
# (IDENTIFY, DEFINE, DESIGN, ALIGN, REFINE) or in-game vocabulary (OUTCOME,
# RUBRIC, ALIGNMENT) so they're never confused on the projector.
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
            "earned": 0,
            "lost": 0,
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
    """Arcade-style skin for the team screens. Scoped size rules rely on
    Streamlit's per-widget `st-key-<key>` class (Streamlit >= 1.39); on older
    versions they are ignored and the app still works."""

    st.markdown(
        """
        <style>
        /* Use the full projector width instead of a narrow centered column */
        .block-container {
            max-width: 100% !important;
            padding: 1rem 2.2rem 1rem 2.2rem !important;
        }

        /* ---------- HUD ---------- */
        .hud {
            display:flex; align-items:center; justify-content:space-between;
            gap:14px; flex-wrap:wrap;
            background:#101534;
            border:2px solid #2B3566;
            border-radius:16px;
            padding:12px 22px;
            margin-bottom:14px;
        }
        .hud-team {
            font-family:'Trebuchet MS', sans-serif;
            font-size:30px; font-weight:800; color:#FFFFFF; line-height:1.1;
        }
        .hud-sub { font-size:15px; color:#98A2D8; margin-top:2px; }
        .hud-stat {
            background:#1B2350; border-radius:12px; padding:6px 18px;
            text-align:center; min-width:130px;
        }
        .hud-stat .val {
            font-size:28px; font-weight:800; color:#FFD43B; line-height:1.15;
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
            padding:20px 26px;
            box-shadow:0 7px 0 #101534;
            margin-bottom:16px;
        }
        .qcard .qtitle {
            font-family:'Trebuchet MS', sans-serif;
            font-size:28px; font-weight:800; color:#101534; margin-bottom:10px;
        }
        .qcard .qtext { font-size:22px; line-height:1.5; color:#1F2544; }
        .qhint {
            font-size:17px; color:#4A5280; margin:2px 0 10px 0; font-weight:600;
        }

        /* ---------- Big answer tiles (levels 1, 2, 4) ---------- */
        div[class*="st-key-opt_"] button {
            font-size:21px !important;
            font-weight:700 !important;
            line-height:1.35 !important;
            padding:16px 20px !important;
            border-radius:14px !important;
            border:3px solid #101534 !important;
            text-align:left !important;
            white-space:normal !important;
            height:auto !important;
            box-shadow:0 5px 0 #101534 !important;
        }
        div[class*="st-key-opt_"] button:hover {
            transform:translateY(2px);
            box-shadow:0 3px 0 #101534 !important;
            border-color:#101534 !important;
        }

        /* ---------- Level 3 block pieces: visually distinct from answers --- */
        div[class*="st-key-block_"] button {
            font-size:20px !important;
            font-weight:700 !important;
            padding:14px 18px !important;
            border-radius:999px !important;          /* pill, not tile */
            border:2px dashed #4C6EF5 !important;
            background:#EEF2FF !important;
            color:#20306B !important;
            box-shadow:none !important;
            text-align:left !important;
            white-space:normal !important;
            height:auto !important;
        }
        div[class*="st-key-block_"] button:hover {
            background:#DCE4FF !important;
            border-style:solid !important;
        }
        div[class*="st-key-block_"] button:disabled {
            background:#F1F3F9 !important;
            color:#A8AEC6 !important;
            border:2px dashed #CFD4E6 !important;
        }

        /* ---------- Action buttons ---------- */
        div[class*="st-key-submit_"] button {
            font-size:20px !important; font-weight:800 !important;
            padding:14px 18px !important; border-radius:14px !important;
            border:3px solid #101534 !important;
            box-shadow:0 5px 0 #101534 !important;
        }

        /* ---------- Word-search cells stay compact ---------- */
        div[class*="st-key-cell_"] button {
            font-size:19px !important; font-weight:800 !important;
            padding:4px 0 !important; border-radius:8px !important;
            min-height:42px !important;
        }

        /* ---------- Level 3 build zone ---------- */
        .buildzone {
            background:#101534; border-radius:16px;
            padding:14px 18px; margin-bottom:14px;
        }
        .bz-head {
            font-family:'Trebuchet MS', sans-serif;
            font-size:17px; font-weight:800; color:#98A2D8;
            letter-spacing:1px; margin-bottom:10px;
        }
        .bz-slot {
            display:flex; align-items:center; gap:12px;
            border-radius:10px; padding:9px 14px; margin-bottom:6px;
            font-size:20px; font-weight:700;
        }
        .bz-slot.filled { background:#FFD43B; color:#101534; }
        .bz-slot.empty  {
            background:transparent; color:#5C6699;
            border:2px dashed #3A4580; font-weight:600; font-style:italic;
        }
        .bz-slot .pos {
            width:28px; height:28px; flex:none; border-radius:50%;
            background:#101534; color:#FFD43B;
            display:flex; align-items:center; justify-content:center;
            font-size:15px; font-weight:800;
        }
        .bz-slot.empty .pos { background:#1B2350; color:#5C6699; }

        /* ---------- Side panels ---------- */
        .panel {
            background:#F6F7FC; border:2px solid #D7DBEF;
            border-radius:16px; padding:14px 18px; margin-bottom:14px;
        }
        .panel-head {
            font-family:'Trebuchet MS', sans-serif;
            font-size:17px; font-weight:800; color:#101534;
            letter-spacing:.5px; margin-bottom:10px;
        }
        .step {
            display:flex; align-items:center; gap:10px;
            font-size:16px; line-height:1.35;
            padding:6px 8px; border-radius:9px; margin-bottom:3px;
        }
        .step .num {
            width:26px; height:26px; flex:none; border-radius:50%;
            display:flex; align-items:center; justify-content:center;
            font-size:13px; font-weight:800; color:#FFFFFF;
        }
        .step.done { color:#1F2544; font-weight:700; background:#EDFBF0; }
        .step.now  { color:#101534; font-weight:700; background:#FFF8E1;
                     box-shadow:inset 0 0 0 2px #F59F00; }
        .step.todo { color:#8A90AE; }

        .statrow {
            display:flex; justify-content:space-between; align-items:baseline;
            font-size:17px; padding:5px 0; border-bottom:1px solid #E4E7F3;
        }
        .statrow:last-child { border-bottom:none; }
        .statrow .k { color:#5A6187; }
        .statrow .v { font-weight:800; color:#101534; font-size:19px; }
        .statrow .v.up   { color:#2B8A3E; }
        .statrow .v.down { color:#C92A2A; }
        </style>
        """,
        unsafe_allow_html=True
    )


# --------------------------------------------------------------------------
# Panels
# --------------------------------------------------------------------------
def pyramid(level, show_locked_names=False):
    """Projector-friendly pyramid of colored bricks. Completed levels show
    their name; locked ones can show a greyed name so teams can see the whole
    ladder ahead of them."""
    widths = [30, 45, 60, 75, 90]
    rows = []

    for i in range(4, -1, -1):
        completed = i < level
        current = (i == level) and show_locked_names

        if completed:
            color, text_color, label = LEVEL_COLORS[i], "#FFFFFF", LEVELS[i]
        elif current:
            color, text_color, label = "#FFF3BF", "#8A6100", f"▶ {LEVELS[i]}"
        elif show_locked_names:
            color, text_color, label = "#E9ECEF", "#ADB5BD", LEVELS[i]
        else:
            color, text_color, label = "#E9ECEF", "#ADB5BD", "🔒"

        border = "2px solid #F59F00" if current else "none"

        rows.append(
            f'''
            <div style="
                width:{widths[i]}%;
                margin:3px auto;
                background:{color};
                color:{text_color};
                border:{border};
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
    """Team name, current level (with its name) and coin wallet."""
    if t["level"] > 5:
        level_label = "COMPLETE"
    else:
        level_label = f"{t['level']} · {LEVELS[t['level'] - 1]}"

    st.markdown(
        f"""
        <div class="hud">
            <div>
                <div class="hud-team">🏗️ {t['name']}</div>
                <div class="hud-sub">{sum(t['completed'])} of 5 levels cleared ·
                    {t['misses']} wrong attempt(s)</div>
            </div>
            <div style="display:flex;gap:12px;">
                <div class="hud-stat level">
                    <div class="val">{level_label}</div>
                    <div class="lbl">CURRENT LEVEL</div>
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
            state, badge = "done", "✓"
        elif current:
            state, badge = "now", str(i + 1)
        else:
            state, badge = "todo", "🔒"

        bg = LEVEL_COLORS[i] if done else ("#F59F00" if current else "#C6CADB")

        rows.append(
            f"<div class='step {state}'>"
            f"<span class='num' style='background:{bg};'>{badge}</span>"
            f"<span>{LEVELS[i]} — {step}</span>"
            f"</div>"
        )

    cleared = sum(t["completed"])

    return (
        "<div class='panel'>"
        f"<div class='panel-head'>Your OBE design — {cleared} of 5 complete</div>"
        + "".join(rows) +
        "</div>"
    )


def performance_html(t):
    """Coins earned, coins lost and overall progress at a glance."""
    cleared = sum(t["completed"])
    attempts = cleared + t["misses"]
    accuracy = f"{round(100 * cleared / attempts)}%" if attempts else "—"

    return f"""
    <div class='panel'>
        <div class='panel-head'>Your performance</div>
        <div class='statrow'><span class='k'>Wallet now</span>
            <span class='v'>🪙 {t['coins']}</span></div>
        <div class='statrow'><span class='k'>Earned from levels</span>
            <span class='v up'>+{t['earned']}</span></div>
        <div class='statrow'><span class='k'>Lost to wrong answers</span>
            <span class='v down'>−{t['lost']}</span></div>
        <div class='statrow'><span class='k'>Levels cleared</span>
            <span class='v'>{cleared} / 5</span></div>
        <div class='statrow'><span class='k'>First-try accuracy</span>
            <span class='v'>{accuracy}</span></div>
    </div>
    """


def side_panels(t):
    st.markdown(
        f"<div class='panel'><div class='panel-head'>Your pyramid</div>"
        f"{pyramid(sum(t['completed']), show_locked_names=True)}"
        f"</div>",
        unsafe_allow_html=True
    )
    st.markdown(steps_html(t), unsafe_allow_html=True)
    st.markdown(performance_html(t), unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Feedback animations
# --------------------------------------------------------------------------
def correct_popup(message, reward):
    """Green tick that pops in, plus a confetti burst and the coin gain."""
    components.html(
        f"""
        <script src="https://cdnjs.cloudflare.com/ajax/libs/canvas-confetti/1.9.2/confetti.browser.min.js"></script>
        <style>
        .pop-wrap {{ font-family:'Trebuchet MS', sans-serif; text-align:center; padding-top:6px; }}
        .pop-tick {{
            width:100px; height:100px; margin:0 auto; border-radius:50%;
            background:#40C057; color:#FFFFFF; font-size:58px; font-weight:800;
            display:flex; align-items:center; justify-content:center;
            box-shadow:0 0 0 10px rgba(64,192,87,0.25);
            animation:pop .45s cubic-bezier(.17,.89,.32,1.49);
        }}
        .pop-msg {{ font-size:25px; font-weight:800; color:#2B8A3E; margin-top:12px; }}
        .pop-coins {{ font-size:21px; font-weight:700; color:#B08900; margin-top:4px;
                      animation:rise .7s ease-out; }}
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
                }} else {{ setTimeout(fire, 100); }}
            }}
            fire();
        }})();
        </script>
        """,
        height=245,
    )


def penalty_popup(message, penalty, coins_left):
    """Red cross with the coins floating away — shown after a wrong answer."""
    components.html(
        f"""
        <style>
        .miss-wrap {{
            font-family:'Trebuchet MS', sans-serif;
            display:flex; align-items:center; gap:16px;
            background:#FFF5F5; border:3px solid #F03E3E;
            border-radius:16px; padding:14px 20px;
            animation:shake .4s ease-in-out;
        }}
        .miss-x {{
            width:58px; height:58px; flex:none; border-radius:50%;
            background:#F03E3E; color:#FFFFFF; font-size:31px; font-weight:800;
            display:flex; align-items:center; justify-content:center;
        }}
        .miss-msg {{ font-size:21px; font-weight:700; color:#C92A2A; }}
        .miss-sub {{ font-size:16px; color:#862E2E; margin-top:3px; }}
        .miss-cost {{ margin-left:auto; font-size:28px; font-weight:800; color:#F03E3E; }}
        @keyframes shake {{
            0%,100% {{ transform:translateX(0); }}
            25%     {{ transform:translateX(-9px); }}
            75%     {{ transform:translateX(9px); }}
        }}
        @media (prefers-reduced-motion: reduce) {{ .miss-wrap {{ animation:none; }} }}
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
        height=115,
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
            audio.play().catch(function(e) {{ console.log("Audio blocked:", e); }});
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
    t["earned"] += LEVEL_REWARD


def charge_miss(team_id, message):
    """Deduct coins for a wrong attempt and queue the penalty animation."""
    t = teams[team_id]
    charged = min(WRONG_PENALTY, t["coins"])

    t["misses"] += 1
    t["coins"] -= charged
    t["lost"] += charged

    st.session_state[f"flash_{team_id}"] = {
        "message": message,
        "penalty": charged,
        "coins": t["coins"],
    }


def show_flash(team_id):
    flash = st.session_state.pop(f"flash_{team_id}", None)

    if flash:
        penalty_popup(flash["message"], flash["penalty"], flash["coins"])


def complete_level(team_id, level):
    """Shared success path: advance, pay out, celebrate, and name the OBE
    move the team just completed."""
    advance(team_id, level)

    correct_popup(
        f"LEVEL {level} — {LEVELS[level - 1]} CLEARED",
        LEVEL_REWARD
    )

    nxt = (
        "Pyramid complete!"
        if level == 5
        else f"Next up: Level {level + 1} — {LEVELS[level]}"
    )

    st.markdown(
        f"<div style='font-family:Trebuchet MS,sans-serif;text-align:center;"
        f"font-size:23px;font-weight:800;color:#101534;margin:4px 0 6px 0;'>"
        f"You have {OBE_STEPS[level - 1][0].lower()}{OBE_STEPS[level - 1][1:]}.</div>"
        f"<div style='text-align:center;font-size:19px;color:#4A5280;"
        f"margin-bottom:10px;'>{nxt}</div>",
        unsafe_allow_html=True
    )

    # SOUND PLAYS ONLY ON THIS TEAM'S DEVICE
    play_level_sound()

    time.sleep(3.0)


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
        if st.button("👥 JOIN AS TEAM", use_container_width=True, type="primary"):
            st.session_state.page = "join"
            st.rerun()

    with b:
        if st.button("📺 PRESENTER DASHBOARD", use_container_width=True):
            st.session_state.page = "presenter"
            st.rerun()


def join():
    st.title("👥 Join OBE Level-Up")

    team = st.selectbox("Select your team", [t["name"] for t in teams.values()])
    team_id = next(i for i, tm in teams.items() if tm["name"] == team)
    t = teams[team_id]

    if t["level"] > 5:
        st.info(f"**{t['name']}** has completed all levels! 🏆 • 🪙 {t['coins']} coins")
    else:
        st.info(
            f"**{t['name']}** is on Level {t['level']} — {LEVELS[t['level'] - 1]}"
            f"  •  🪙 {t['coins']} coins"
        )

    if st.button("ENTER GAME", type="primary", use_container_width=True):
        st.session_state.team = team_id
        st.session_state.page = "team"
        st.rerun()

    if st.button("← Back"):
        st.session_state.page = "home"
        st.rerun()


def render_choice_level(team_id, level):
    """Levels 1, 2 and 4 — tap one big answer tile."""
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

        if st.button(
            f"{chr(65 + pos)}.  {options[idx]}",
            key=f"opt_{team_id}_{level}_{pos}",
            use_container_width=True
        ):
            if idx == QUESTIONS[level]["answer"]:
                st.session_state.pop(order_key, None)
                complete_level(team_id, level)
            else:
                charge_miss(team_id, "Not the one. Talk it over and pick again.")

            st.rerun()


def render_sequence_level(team_id):
    """Level 3 — tap dashed block pills to fill the numbered build zone."""
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
    total = len(pool)

    # --- build zone: the answer being constructed ---
    slots = []

    for n in range(total):
        if n < len(sequence):
            slots.append(
                f"<div class='bz-slot filled'><span class='pos'>{n + 1}</span>"
                f"<span>{sequence[n]}</span></div>"
            )
        else:
            slots.append(
                f"<div class='bz-slot empty'><span class='pos'>{n + 1}</span>"
                f"<span>empty</span></div>"
            )

    st.markdown(
        "<div class='buildzone'>"
        "<div class='bz-head'>YOUR SEQUENCE — teacher support ➜ independence</div>"
        + "".join(slots) +
        "</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<div class='qhint'>Tap a block below to drop it into the next empty slot.</div>",
        unsafe_allow_html=True
    )

    for n, block in enumerate(pool):

        used = block in sequence

        if st.button(
            ("✔  " if used else "➕  ") + block,
            key=f"block_{team_id}_3_{n}",
            use_container_width=True,
            disabled=used
        ):
            sequence.append(block)
            st.rerun()

    c1, c2, c3 = st.columns(3)

    if c1.button("↶ Undo", key="submit_undo_3", use_container_width=True,
                 disabled=not sequence):
        sequence.pop()
        st.rerun()

    if c2.button("↺ Clear", key="submit_clear_3", use_container_width=True,
                 disabled=not sequence):
        st.session_state[seq_key] = []
        st.rerun()

    if c3.button("🚀 Lock in", key="submit_seq_3", type="primary",
                 use_container_width=True, disabled=len(sequence) < total):

        if sequence == QUESTIONS[3]["answer"]:
            st.session_state.pop(pool_key, None)
            st.session_state.pop(seq_key, None)
            complete_level(team_id, 3)
        else:
            st.session_state[seq_key] = []
            charge_miss(
                team_id,
                "Not yet — move from teacher support toward independence."
            )

        st.rerun()


def render_word_search(team_id, t):
    """Level 5 — laid out full width: grid | clues | progress panels."""
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

    grid_col, clue_col, side_col = st.columns([2.4, 1.5, 1.1])

    with grid_col:
        st.markdown(
            "<div class='qcard'><div class='qtitle'>🔁 LEVEL 5 — REFINE THE LOOP</div>"
            "<div class='qtext'>Three words are hidden in the grid. Tap letters to "
            "spell a word, then submit it. A wrong word costs coins.</div></div>",
            unsafe_allow_html=True
        )

        for r in range(WORD_SEARCH_SIZE):

            row_cells = st.columns(WORD_SEARCH_SIZE, gap="small")

            for c in range(WORD_SEARCH_SIZE):

                is_selected = (r, c) in selected

                if row_cells[c].button(
                    grid[r][c],
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
        st.markdown("<div class='panel-head'>Clues</div>", unsafe_allow_html=True)

        for w in WORD_SEARCH_WORDS:
            icon = "✅" if w["answer"] in found else "🔲"
            st.markdown(
                f"<div style='font-size:18px;line-height:1.45;margin-bottom:8px;'>"
                f"{icon} {w['clue']} <i>({len(w['answer'])} letters)</i></div>",
                unsafe_allow_html=True
            )

        current_word = "".join(grid[r][c] for r, c in selected)

        st.markdown(
            f"<div style='font-size:28px;font-weight:800;letter-spacing:4px;"
            f"background:#101534;color:#FFD43B;border-radius:12px;"
            f"padding:12px;text-align:center;margin:10px 0;min-height:52px;'>"
            f"{current_word or '&nbsp;'}</div>",
            unsafe_allow_html=True
        )

        b1, b2 = st.columns(2)

        if b1.button("↺ Clear", key="submit_clear_5", use_container_width=True):
            st.session_state[sel_key] = []
            st.rerun()

        if b2.button("🚀 Submit", key="submit_word_5", type="primary",
                     use_container_width=True, disabled=not current_word):

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
                    complete_level(team_id, 5)
                else:
                    remaining = len(WORD_SEARCH_WORDS) - len(found)
                    st.markdown(
                        f"<div style='font-size:21px;font-weight:700;color:#2B8A3E;'>"
                        f"✅ {match} found — {remaining} to go.</div>",
                        unsafe_allow_html=True
                    )
                    time.sleep(1.2)
            else:
                charge_miss(team_id, "That isn't one of the hidden words.")

            st.rerun()

    with side_col:
        side_panels(t)


def team_game():
    inject_game_css()

    team_id = st.session_state.team
    t = teams[team_id]
    level = t["level"]

    hud(t)

    # ---- Finished ----
    if level > 5:
        main, side = st.columns([2, 1])

        with main:
            st.markdown(
                "<div class='qcard'><div class='qtitle'>🏆 OBE MASTER — PYRAMID COMPLETE</div>"
                f"<div class='qtext'>Final wallet: 🪙 {t['coins']} coins after "
                f"{t['misses']} wrong attempt(s). You identified the need, defined the "
                f"outcome, designed the activity, aligned the assessment, and refined "
                f"the loop.</div></div>",
                unsafe_allow_html=True
            )
            st.markdown(pyramid(5, show_locked_names=True), unsafe_allow_html=True)

            if not t["celebrated_team"]:
                correct_popup(f"{t['name']} finished the pyramid!", LEVEL_REWARD)
                t["celebrated_team"] = True

        with side:
            st.markdown(steps_html(t), unsafe_allow_html=True)
            st.markdown(performance_html(t), unsafe_allow_html=True)

        if st.button("← Leave game"):
            st.session_state.page = "home"
            st.rerun()

        return

    # ---- Level 5 has its own full-width layout ----
    if level == 5:
        show_flash(team_id)
        render_word_search(team_id, t)

    else:
        main, side = st.columns([2, 1])

        with main:
            show_flash(team_id)

            st.markdown(
                f"<div class='qcard'>"
                f"<div class='qtitle'>{QUESTIONS[level]['title']}</div>"
                f"<div class='qtext'>{QUESTIONS[level]['text']}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

            if level in (1, 2, 4):
                render_choice_level(team_id, level)
            else:
                render_sequence_level(team_id)

        with side:
            side_panels(t)

    if st.button("← Leave game"):
        st.session_state.page = "home"
        st.rerun()


def presenter():

    # Silently reruns this page every 2 seconds so scores/pyramids update
    # on the projector without anyone clicking Refresh.
    st_autorefresh(interval=2000, key="presenter_autorefresh")

    st.markdown(
        """
        <style>
        .block-container { max-width:100% !important;
            padding: 1rem 1.6rem 0.5rem 1.6rem !important; }
        div[data-testid="stVerticalBlock"] > div { gap: 0.3rem; }
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
        done = sum(t["completed"])

        just_finished = t["level"] > 5 and not t["celebrated_presenter"]

        with col:
            st.markdown(
                f"<h4 style='text-align:center;margin:0;' title='Team {i}'>{t['name']}</h4>",
                unsafe_allow_html=True
            )

            status = (
                "🏆 COMPLETE"
                if t["level"] > 5
                else f"L{t['level']} · {LEVELS[t['level'] - 1]}"
            )

            st.markdown(
                f"<div style='text-align:center;font-size:17px;font-weight:800;"
                f"color:{'#F03E3E' if t['level']>5 else '#212529'};margin-bottom:2px;'>"
                f"{status}</div>",
                unsafe_allow_html=True
            )

            st.markdown(
                f"<div style='text-align:center;font-size:23px;font-weight:800;"
                f"color:#B08900;margin-bottom:4px;'>🪙 {t['coins']}</div>",
                unsafe_allow_html=True
            )

            st.markdown(pyramid(done), unsafe_allow_html=True)
            st.progress(done / 5)

            st.markdown(
                f"<div style='text-align:center;font-size:13px;color:#666;margin-top:2px;'>"
                f"{done}/5 levels • +{t['earned']} / −{t['lost']}</div>",
                unsafe_allow_html=True
            )

            if just_finished:
                correct_popup(f"{t['name']} finished the pyramid!", LEVEL_REWARD)
                t["celebrated_presenter"] = True

    st.divider()

    st.markdown(
        "<h4 style='margin:0.2rem 0;'>📋 Level-by-Level Progress</h4>",
        unsafe_allow_html=True
    )

    header = st.columns(6)
    header[0].markdown("**TEAM**")

    for i, name in enumerate(LEVELS, start=1):
        header[i].markdown(f"**{i}. {name}**")

    for i in range(1, 7):

        t = teams[i]
        row = st.columns(6)
        row[0].markdown(f"**{t['name']}**")

        for j in range(5):

            done = t["completed"][j]
            color = LEVEL_COLORS[j] if done else "#E9ECEF"
            text = LEVELS[j] if done else ""

            row[j + 1].markdown(
                f"<div style='background:{color};border-radius:6px;height:28px;"
                f"display:flex;align-items:center;justify-content:center;"
                f"color:white;font-weight:700;font-size:12px;letter-spacing:1px;'>"
                f"{text}</div>",
                unsafe_allow_html=True
            )

    c1, c2 = st.columns(2)

    with c1:
        if st.button("🔄 Refresh Dashboard", use_container_width=True):
            st.rerun()

    with c2:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()


def demo():

    st.title("⚙️ Demo Control")
    st.caption("Use this to test the presenter screen before the real multiplayer version.")

    for i in range(1, 7):

        t = teams[i]
        c1, c2 = st.columns([2, 1])

        status = "COMPLETE" if t["level"] > 5 else f"Level {t['level']} — {LEVELS[t['level'] - 1]}"

        c1.write(f"**{t['name']}** (Team {i}) — {status} • 🪙 {t['coins']}")

        if c2.button(f"Advance Team {i}", key=f"advance_{i}"):

            if t["level"] <= 5:
                advance(i, t["level"])

            st.rerun()

    if st.button("Reset All Teams"):

        for i in range(1, 7):

            teams[i].update({
                "level": 1,
                "score": 0,
                "coins": START_COINS,
                "earned": 0,
                "lost": 0,
                "misses": 0,
                "completed": [False] * 5,
                "name": DEFAULT_TEAM_NAMES[i],
                "celebrated_team": False,
                "celebrated_presenter": False,
            })

            for key in (f"l5_grid_{i}", f"l5_selected_{i}", f"l5_found_{i}",
                        f"pool_{i}_3", f"seq_{i}_3", f"flash_{i}"):
                st.session_state.pop(key, None)

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
