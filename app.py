import streamlit as st
import time

st.set_page_config(page_title="OBE Level-Up", page_icon="🏗️", layout="wide")

LEVELS = ["IDENTIFY", "DEFINE", "DESIGN", "ALIGN", "REFINE"]

# One color per level — used for the projector pyramid bricks
LEVEL_COLORS = ["#4C6EF5", "#15AABF", "#40C057", "#F59F00", "#F03E3E"]

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

if "teams" not in st.session_state:
    st.session_state.teams = {
        i: {"level": 1, "score": 0, "completed": [False] * 5}
        for i in range(1, 6)
    }

if "page" not in st.session_state:
    st.session_state.page = "home"

if "team" not in st.session_state:
    st.session_state.team = None


def pyramid(level):
    """Render a projector-friendly pyramid using colored HTML bricks
    instead of monospace block characters."""
    widths = [30, 45, 60, 75, 90]  # percent width, narrow at top -> wide at base
    rows = []
    # Build top-to-bottom so it visually looks like a pyramid (level 5 label on top)
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


def advance(team_id, level):
    t = st.session_state.teams[team_id]
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
    st.info("Five teams. Five challenges. Complete each level to build your OBE pyramid.")

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
    team = st.selectbox("Select your team", [f"Team {i}" for i in range(1, 6)])
    team_id = int(team.split()[-1])

    t = st.session_state.teams[team_id]
    st.info(f"{team} is currently on Level {t['level']}.")

    if st.button("ENTER GAME", type="primary", use_container_width=True):
        st.session_state.team = team_id
        st.session_state.page = "team"
        st.rerun()

    if st.button("← Back"):
        st.session_state.page = "home"
        st.rerun()


def team_game():
    team_id = st.session_state.team
    t = st.session_state.teams[team_id]
    level = t["level"]

    st.title(f"🏗️ Team {team_id}")

    if level > 5:
        st.success("🏆 OBE MASTER — YOUR PYRAMID IS COMPLETE!")
        st.markdown(pyramid(5), unsafe_allow_html=True)
        return

    st.progress((level - 1) / 5)
    st.subheader(QUESTIONS[level]["title"])
    st.write(QUESTIONS[level]["text"])

    if level in [1, 2, 4]:
        options = QUESTIONS[level]["options"]
        choice = st.radio(
            "Choose your team's response:",
            range(len(options)),
            format_func=lambda x: options[x],
            key=f"q_{team_id}_{level}"
        )

        if st.button("SUBMIT CHALLENGE", type="primary", use_container_width=True):
            if choice == QUESTIONS[level]["answer"]:
                advance(team_id, level)
                st.success(f"🎉 Level {level} complete! Level {level + 1} unlocked.")
                time.sleep(0.6)
                st.rerun()
            else:
                st.error("Not quite. Discuss it and try again.")

    elif level == 3:
        st.write("Select the blocks in the order your team recommends.")
        selected = st.multiselect(
            "Build your sequence:",
            QUESTIONS[3]["options"],
            key=f"q_{team_id}_3"
        )

        if st.button("SUBMIT SEQUENCE", type="primary", use_container_width=True):
            if selected == QUESTIONS[3]["answer"]:
                advance(team_id, 3)
                st.success("🎉 Level 3 complete! Level 4 unlocked.")
                time.sleep(0.6)
                st.rerun()
            else:
                st.error("Reconsider the movement from support toward independence.")


def presenter():
    st.markdown(
        "<h1 style='text-align:center;'>📺 OBE LEVEL-UP — LIVE PRESENTER DASHBOARD</h1>",
        unsafe_allow_html=True
    )
    st.caption("Project this screen. Each team uses a separate device.")

    cols = st.columns(5)

    for i, col in enumerate(cols, start=1):
        t = st.session_state.teams[i]
        level = min(t["level"], 5)
        done = sum(t["completed"])

        with col:
            st.markdown(
                f"<h3 style='text-align:center;'>Team {i}</h3>",
                unsafe_allow_html=True
            )
            status = "🏆 COMPLETE" if t["level"] > 5 else f"LEVEL {t['level']}"
            st.markdown(
                f"<div style='text-align:center;font-size:22px;font-weight:800;"
                f"color:{'#F03E3E' if t['level']>5 else '#212529'};margin-bottom:6px;'>"
                f"{status}</div>",
                unsafe_allow_html=True
            )
            st.markdown(pyramid(level), unsafe_allow_html=True)
            st.progress(done / 5)
            st.markdown(
                f"<div style='text-align:center;font-size:14px;color:#666;margin-top:4px;'>"
                f"{done}/5 levels • {t['score']} pts</div>",
                unsafe_allow_html=True
            )

    st.divider()

    # ---- Leaderboard, sorted by score, big and readable from a distance ----
    st.subheader("🏆 Leaderboard")
    ranked = sorted(
        st.session_state.teams.items(),
        key=lambda kv: (-kv[1]["score"], -sum(kv[1]["completed"]))
    )
    medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    lb_cols = st.columns(5)
    for rank, (team_id, t) in enumerate(ranked):
        with lb_cols[rank]:
            st.markdown(
                f"<div style='text-align:center;font-size:34px;'>{medal[rank]}</div>"
                f"<div style='text-align:center;font-size:18px;font-weight:700;'>Team {team_id}</div>"
                f"<div style='text-align:center;font-size:15px;color:#666;'>{t['score']} pts</div>",
                unsafe_allow_html=True
            )

    st.divider()

    # ---- Live progress grid with colored badges instead of emoji lock/check ----
    st.subheader("Live Progress")

    header = st.columns(6)
    header[0].markdown("**TEAM**")
    for i, name in enumerate(LEVELS, start=1):
        header[i].markdown(f"**{i}. {name}**")

    for i in range(1, 6):
        t = st.session_state.teams[i]
        row = st.columns(6)
        row[0].markdown(f"**Team {i}**")
        for j in range(5):
            done = t["completed"][j]
            color = LEVEL_COLORS[j] if done else "#E9ECEF"
            text = "✓" if done else ""
            row[j + 1].markdown(
                f"<div style='background:{color};border-radius:6px;height:32px;"
                f"display:flex;align-items:center;justify-content:center;"
                f"color:white;font-weight:700;'>{text}</div>",
                unsafe_allow_html=True
            )

    st.write("")
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

    for i in range(1, 6):
        t = st.session_state.teams[i]
        c1, c2 = st.columns([2, 1])
        c1.write(f"Team {i} — Level {t['level']}")
        if c2.button(f"Advance Team {i}", key=f"advance_{i}"):
            if t["level"] <= 5:
                advance(i, t["level"])
            st.rerun()

    if st.button("Reset All Teams"):
        st.session_state.teams = {
            i: {"level": 1, "score": 0, "completed": [False] * 5}
            for i in range(1, 6)
        }
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
