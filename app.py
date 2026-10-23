
import json
import random
import sqlite3
import time
from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# --------------------------------------------------
# 1. APPLICATION SETTINGS
# --------------------------------------------------

st.set_page_config(
    page_title="COPA Online Examination",
    page_icon="🎓",
    layout="wide"
)

DB_NAME = "copa_exam.db"

SUBJECTS = [
    "LO 1",
    "LO 2",
    "LO 3",
    "LO 4"
]


# --------------------------------------------------
# 2. DATABASE CONNECTION AND TABLES
# --------------------------------------------------

def connect_db():
    return sqlite3.connect(DB_NAME)


def initialize_database():
    with connect_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS trainees (
                roll_no TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                question TEXT NOT NULL,
                options_json TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                marks INTEGER NOT NULL DEFAULT 1
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roll_no TEXT NOT NULL,
                name TEXT NOT NULL,
                subject TEXT NOT NULL,
                score INTEGER NOT NULL,
                total INTEGER NOT NULL,
                percentage REAL NOT NULL,
                started_at TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                details_json TEXT NOT NULL
            )
        """)

        count = con.execute(
            "SELECT COUNT(*) FROM questions"
        ).fetchone()[0]

        # Insert demonstration questions only when empty.
       
# --------------------------------------------------
# 3. INITIAL QUESTION BANK
# --------------------------------------------------



# --------------------------------------------------
# 4. TRAINEE REGISTRATION
# --------------------------------------------------

def save_trainee(roll_no, name):
    with connect_db() as con:
        con.execute("""
            INSERT INTO trainees (roll_no, name)
            VALUES (?, ?)
            ON CONFLICT(roll_no)
            DO UPDATE SET name = excluded.name
        """, (roll_no, name))


# --------------------------------------------------
# 5. GET QUESTIONS
# --------------------------------------------------

def get_questions(subject):
    with connect_db() as con:
        rows = con.execute("""
            SELECT id, subject, topic, question,
                   options_json, correct_answer, marks
            FROM questions
            WHERE subject = ?
        """, (subject,)).fetchall()

    questions = []

    for row in rows:
        questions.append({
            "id": row[0],
            "subject": row[1],
            "topic": row[2],
            "question": row[3],
            "options": json.loads(row[4]),
            "correct_answer": row[5],
            "marks": row[6]
        })

    return questions


# --------------------------------------------------
# 6. SAVE EXAM RESULT
# --------------------------------------------------

def submit_exam(auto=False):
    exam = st.session_state.get("active_exam")

    if not exam:
        return

    score = 0
    total = 0
    details = []

    for q in exam["questions"]:
        selected = st.session_state.get(
            f"answer_{q['id']}"
        )

        correct = selected == q["correct_answer"]
        marks = q["marks"]
        total += marks

        if correct:
            score += marks

        details.append({
            "question_id": q["id"],
            "question": q["question"],
            "topic": q["topic"],
            "selected": selected or "Not answered",
            "correct_answer": q["correct_answer"],
            "is_correct": correct,
            "marks_awarded": marks if correct else 0,
            "marks_available": marks,
        })

    percentage = round(score / total * 100, 2) if total else 0
    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with connect_db() as con:
        con.execute("""
            INSERT INTO results (
                roll_no, name, subject, score, total,
                percentage, started_at, submitted_at,
                details_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exam["roll_no"],
            exam["name"],
            exam["subject"],
            score,
            total,
            percentage,
            exam["started_at"],
            submitted_at,
            json.dumps(details)
        ))

        result_id = con.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

    st.session_state["last_result"] = {
        "id": result_id,
        "roll_no": exam["roll_no"],
        "name": exam["name"],
        "subject": exam["subject"],
        "score": score,
        "total": total,
        "percentage": percentage,
        "details": details,
        "auto": auto
    }

    st.session_state["active_exam"] = None


# --------------------------------------------------
# 7. PROFESSIONAL SIDEBAR LINK NAVIGATION
# --------------------------------------------------

st.markdown("""
<style>
    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(128, 128, 128, 0.25);
    }
    [data-testid="stSidebar"] h2 {
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.07);
        border: 1px solid rgba(128, 128, 128, 0.18);
        padding: 14px;
        border-radius: 12px;
    }
    [data-testid="stSidebar"] div.stButton > button {
        width: 100%;
        text-align: left;
        justify-content: flex-start;
        border: 1px solid transparent;
        border-radius: 9px;
        padding: 0.62rem 0.78rem;
        margin: 2px 0;
        background: transparent;
        color: inherit;
        font-size: 15px;
        font-weight: 500;
        transition: background 0.15s ease, border-color 0.15s ease;
    }
    [data-testid="stSidebar"] div.stButton > button:hover {
        background: rgba(37, 99, 235, 0.10);
        border-color: rgba(37, 99, 235, 0.25);
        color: #2563EB;
    }
    [data-testid="stSidebar"] div.stButton > button:focus:not(:active) {
        border-color: rgba(37, 99, 235, 0.30);
        box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.15);
    }
    .dashboard-section-heading { font-size: 1.35rem; font-weight: 750; letter-spacing: -0.3px; margin: 0 0 4px 0; }
    .dashboard-section-subtitle { color: var(--text-color); opacity: 0.72; font-size: 0.92rem; margin: 0 0 16px 0; }
    .subject-card { min-height: 158px; padding: 19px 18px 17px; margin-bottom: 14px; border: 1px solid rgba(128,128,128,.22); border-radius: 16px; background: linear-gradient(145deg, rgba(37,99,235,.075), rgba(128,128,128,.035)); box-shadow: 0 3px 12px rgba(0,0,0,.035); transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease; }
    .subject-card:hover { transform: translateY(-3px); border-color: rgba(37,99,235,.48); box-shadow: 0 8px 22px rgba(37,99,235,.09); }
    .subject-card-top { display: flex; align-items: center; gap: 12px; margin-bottom: 15px; }
    .subject-icon { display:flex; align-items:center; justify-content:center; width:46px; height:46px; flex-shrink:0; border-radius:13px; background:rgba(37,99,235,.13); font-size:25px; }
    .subject-kicker { font-size:10px; font-weight:750; letter-spacing:1.1px; text-transform:uppercase; opacity:.65; margin-bottom:3px; }
    .subject-name { font-size:16px; line-height:1.3; font-weight:750; overflow-wrap:anywhere; }
    .subject-count-row { display:flex; align-items:center; justify-content:space-between; gap:8px; border-top:1px solid rgba(128,128,128,.19); padding-top:12px; }
    .subject-count-label { font-size:12px; opacity:.72; }
    .subject-count { white-space:nowrap; font-size:12px; font-weight:750; color:#2563EB; background:rgba(37,99,235,.12); border-radius:20px; padding:5px 9px; }
    .instruction-card { display:flex; align-items:flex-start; gap:13px; min-height:142px; padding:17px 15px; margin-bottom:12px; border:1px solid rgba(128,128,128,.22); border-radius:15px; background:rgba(128,128,128,.045); transition:border-color .18s ease, background .18s ease; }
    .instruction-card:hover { border-color:rgba(37,99,235,.42); background:rgba(37,99,235,.055); }
    .instruction-number { display:flex; align-items:center; justify-content:center; width:36px; height:36px; flex-shrink:0; border-radius:11px; background:#2563EB; color:white; font-size:14px; font-weight:800; }
    .instruction-heading { font-size:14px; font-weight:750; margin:2px 0 7px; }
    .instruction-detail { font-size:12px; line-height:1.55; opacity:.78; }
    .instruction-step-label { font-size:10px; font-weight:750; letter-spacing:1px; text-transform:uppercase; opacity:.58; margin-bottom:4px; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<div style="text-align:center; padding:16px 4px 10px 4px;">
    <div style="font-size:36px;">🎓</div>
    <h2 style="color:#2563EB; margin:4px 0;">COPA EXAM</h2>
    <p style="font-size:12px; color:gray; margin-top:0;">
        ONLINE EXAMINATION SYSTEM
    </p>
</div>
""", unsafe_allow_html=True)

st.sidebar.divider()
st.sidebar.caption("MAIN MENU")

menu_items = {
    "🏠  Dashboard": "Dashboard",
    "📝  Take Examination": "Take Exam",
    "📚  Question Bank": "Question Bank",
    "📊  Exam Results": "Results",
    "🏆  Rank List": "Rank List",
    "👤  Trainee Performance": "Trainee Performance",
    "📈  Topic Analysis": "Topic Analysis",
}

active_exam = st.session_state.get("active_exam")

if active_exam:
    page = "Take Exam"
    st.sidebar.info("Examination in progress")
    st.sidebar.caption("Navigation is locked until you submit.")
    st.info(
        "An examination is in progress. Finish or submit it before navigating."
    )
else:
    # Use Streamlit buttons for in-app navigation. These stay in the current tab
    # and avoid opening a new browser tab for every menu selection.
    valid_pages = set(menu_items.values())
    if st.session_state.get("current_page") not in valid_pages:
        st.session_state["current_page"] = "Dashboard"

    page = st.session_state["current_page"]
    for label, target_page in menu_items.items():
        button_label = f"✓  {label}" if page == target_page else label
        if st.sidebar.button(
            button_label,
            key=f"nav_{target_page.replace(' ', '_')}",
            use_container_width=True,
            type="secondary",
        ):
            st.session_state["current_page"] = target_page
            st.rerun()
            

st.sidebar.divider()
st.sidebar.caption("COPA Examination Portal")
st.sidebar.caption("Python • Streamlit • SQLite")
st.sidebar.caption("Educational Project | Version 1.0")

# Main page header
st.title("🎓 COPA Online Examination System")
st.caption("Instructor Portal  |  Manage examinations, results and trainee performance")


# --------------------------------------------------
# 8. DASHBOARD
# --------------------------------------------------

if page == "Dashboard":
    st.subheader("Instructor Dashboard")
    st.write("Overview of trainees, examination activity and performance.")

    with connect_db() as con:
        total_trainees = con.execute(
            "SELECT COUNT(*) FROM trainees"
        ).fetchone()[0]

        total_exams = con.execute(
            "SELECT COUNT(*) FROM results"
        ).fetchone()[0]

        question_count = con.execute(
            "SELECT COUNT(*) FROM questions"
        ).fetchone()[0]

        average_marks = con.execute(
            "SELECT AVG(percentage) FROM results"
        ).fetchone()[0]

        recent_results = pd.read_sql_query("""
            SELECT roll_no AS "Roll Number",
                   name AS "Trainee Name",
                   subject AS "Subject",
                   score AS "Score",
                   total AS "Total Marks",
                   percentage AS "Percentage",
                   submitted_at AS "Submitted At"
            FROM results
            ORDER BY submitted_at DESC, id DESC
            LIMIT 10
        """, con)

    average_display = (
        f"{average_marks:.2f}%"
        if average_marks is not None
        else "N/A"
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Trainees", f"{total_trainees:,}")
    col2.metric("Examinations Taken", f"{total_exams:,}")
    col3.metric("Average Marks", average_display)
    col4.metric("Questions in Bank", f"{question_count:,}")

    st.divider()

    # Recent activity table
    st.markdown("### 📋 Recent Examination Results")
    if recent_results.empty:
        st.info("No examination results are available yet. Completed exams will appear here.")
    else:
        recent_results["Percentage"] = recent_results[
            "Percentage"
        ].map(lambda value: f"{value:.2f}%")
        st.dataframe(
            recent_results,
            use_container_width=True,
            hide_index=True
        )

    st.markdown(
        '<div class="dashboard-section-heading">📚 Available Subjects</div>'
        '<div class="dashboard-section-subtitle">Explore the subjects in the question bank and check question availability.</div>',
        unsafe_allow_html=True,
    )

    subject_icons = {
        "Computer Fundamentals": "💻",
        "MS Office": "📊",
        "Python": "🐍",
        "SQL": "🗄️",
        "Networking": "🌐",
    }
    with connect_db() as con:
        subject_counts = dict(con.execute(
            "SELECT subject, COUNT(*) FROM questions GROUP BY subject"
        ).fetchall())

    subject_cols = st.columns(3, gap="medium")
    for index, subject_name in enumerate(SUBJECTS):
        with subject_cols[index % 3]:
            count = subject_counts.get(subject_name, 0)
            st.markdown(
                f'''<div class="subject-card">
                    <div class="subject-card-top">
                        <div class="subject-icon">{subject_icons.get(subject_name, "📘")}</div>
                        <div>
                            <div class="subject-kicker">COPA SUBJECT</div>
                            <div class="subject-name">{subject_name}</div>
                        </div>
                    </div>
                    <div class="subject-count-row">
                        <span class="subject-count-label">Question bank</span>
                        <span class="subject-count">{count} questions</span>
                    </div>
                </div>''',
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div class="dashboard-section-heading" style="margin-top:14px;">🧭 Quick Instructions</div>'
        '<div class="dashboard-section-subtitle">Follow these steps to complete a mock examination successfully.</div>',
        unsafe_allow_html=True,
    )
    instruction_cols = st.columns(4, gap="medium")
    quick_steps = [
        ("01", "Enter Your Details", "Provide the trainee name and roll number correctly."),
        ("02", "Configure Examination", "Choose a subject, duration and number of questions."),
        ("03", "Answer & Submit", "Review your answers and submit before the timer expires."),
        ("04", "Review Your Result", "Check your score and percentage in Exam Results."),
    ]
    for col, (number, heading, detail) in zip(instruction_cols, quick_steps):
        with col:
            st.markdown(
                f'''<div class="instruction-card">
                    <div class="instruction-number">{number}</div>
                    <div>
                        <div class="instruction-step-label">STEP {number}</div>
                        <div class="instruction-heading">{heading}</div>
                        <div class="instruction-detail">{detail}</div>
                    </div>
                </div>''',
                unsafe_allow_html=True,
            )

    st.caption(
        "Dashboard statistics are calculated from the current SQLite database."
    )


# --------------------------------------------------
# 9. START AND CONDUCT AN EXAM
# --------------------------------------------------

if page == "Take Exam" and not active_exam:
    st.subheader("Start Examination")

    with st.form("start_exam_form"):
        name = st.text_input("Trainee name")
        roll_no = st.text_input("Trainee roll number")
        subject = st.selectbox("Select subject", SUBJECTS)
        duration = st.selectbox(
            "Duration",
            [1, 5, 10, 15, 30],
            index=1,
            format_func=lambda x: f"{x} minute(s)"
        )
        question_count = st.number_input(
            "Number of questions",
            min_value=1,
            max_value=30,
            value=3,
            step=1
        )

        confirmed = st.checkbox(
            "I have read the examination instructions."
        )

        start = st.form_submit_button("Start Examination")

    if start:
        if not name.strip() or not roll_no.strip():
            st.error("Enter both trainee name and roll number.")
        elif not confirmed:
            st.warning("Please confirm the instructions.")
        else:
            available = get_questions(subject)

            if not available:
                st.error("No questions are available for this subject.")
            else:
                random.shuffle(available)
                selected_questions = available[:int(question_count)]

                for q in selected_questions:
                    random.shuffle(q["options"])

                save_trainee(roll_no.strip(), name.strip())

                now = time.time()

                st.session_state["active_exam"] = {
                    "name": name.strip(),
                    "roll_no": roll_no.strip(),
                    "subject": subject,
                    "questions": selected_questions,
                    "started_at": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "deadline": now + duration * 60
                }

                st.session_state["last_result"] = None
                st.rerun()


# Render the active examination, including countdown.
active_exam = st.session_state.get("active_exam")

if page == "Take Exam" and active_exam:
    remaining = int(active_exam["deadline"] - time.time())

    if remaining <= 0:
        submit_exam(auto=True)
        st.rerun()

    st_autorefresh(interval=1000, key="exam_timer_refresh")

    remaining = max(0, int(active_exam["deadline"] - time.time()))
    minutes, seconds = divmod(remaining, 60)

    st.subheader(active_exam["subject"])
    st.write(
        f"Trainee: **{active_exam['name']}** | "
        f"Roll number: **{active_exam['roll_no']}**"
    )

    st.metric("Time Remaining", f"{minutes:02d}:{seconds:02d}")
    st.warning("The exam will be submitted automatically when time expires.")

    for i, q in enumerate(active_exam["questions"]):
        st.markdown(f"**Q{i + 1}. {q['question']}**")

        st.radio(
            "Choose one answer",
            q["options"],
            index=None,
            key=f"answer_{q['id']}"
        )

    if st.button("Submit Examination", type="primary"):
        submit_exam(auto=False)
        st.rerun()


# --------------------------------------------------
# 10. DISPLAY THE LAST RESULT
# --------------------------------------------------

if page == "Take Exam" and not st.session_state.get("active_exam"):
    result = st.session_state.get("last_result")

    if result:
        st.subheader("Examination Result")

        if result["auto"]:
            st.warning("Time expired. Your exam was automatically submitted.")

        c1, c2, c3 = st.columns(3)
        c1.metric("Score", f"{result['score']} / {result['total']}")
        c2.metric("Percentage", f"{result['percentage']}%")
        c3.metric(
            "Correct Answers",
            sum(d["is_correct"] for d in result["details"])
        )

        if result["percentage"] >= 40:
            st.success("Practice result: Pass")
        else:
            st.error("Practice result: Needs improvement")

        report = pd.DataFrame(result["details"])
        st.dataframe(report, use_container_width=True)

        st.download_button(
            "Download Individual Mark Sheet (CSV)",
            data=pd.DataFrame([{
                "Result ID": result["id"],
                "Roll Number": result["roll_no"],
                "Name": result["name"],
                "Subject": result["subject"],
                "Score": result["score"],
                "Total Marks": result["total"],
                "Percentage": result["percentage"]
            }]).to_csv(index=False).encode("utf-8"),
            file_name=f"marksheet_{result['roll_no']}_{result['id']}.csv",
            mime="text/csv"
        )


# --------------------------------------------------
# 11. LOAD RESULTS
# --------------------------------------------------

def load_results():
    with connect_db() as con:
        df = pd.read_sql_query("""
            SELECT id, roll_no, name, subject, score, total,
                   percentage, started_at, submitted_at, details_json
            FROM results
            ORDER BY submitted_at DESC
        """, con)

    return df


# --------------------------------------------------
# 12. RESULTS AND DOWNLOAD
# --------------------------------------------------

if page == "Results":
    st.subheader("Examination Results")

    df = load_results()

    if df.empty:
        st.info("No examination results are available.")
    else:
        display = df.drop(columns=["details_json"])
        st.dataframe(display, use_container_width=True)

        st.download_button(
            "Download All Results (CSV)",
            data=display.to_csv(index=False).encode("utf-8"),
            file_name="copa_exam_results.csv",
            mime="text/csv"
        )

        result_id = st.number_input(
            "Enter Result ID for a mark sheet",
            min_value=1,
            step=1
        )

        if st.button("View Mark Sheet"):
            row = df[df["id"] == result_id]

            if row.empty:
                st.error("Result ID not found.")
            else:
                r = row.iloc[0]
                st.markdown("### Individual Mark Sheet")
                st.write("Trainee:", r["name"])
                st.write("Roll number:", r["roll_no"])
                st.write("Subject:", r["subject"])
                st.write("Score:", f"{r['score']} / {r['total']}")
                st.write("Percentage:", f"{r['percentage']}%")

                details = pd.DataFrame(
                    json.loads(r["details_json"])
                )
                st.dataframe(details, use_container_width=True)

                st.download_button(
                    "Download Detailed Mark Sheet",
                    data=details.to_csv(index=False).encode("utf-8"),
                    file_name=f"marksheet_{r['roll_no']}_{r['id']}.csv",
                    mime="text/csv",
                    key=f"download_{int(result_id)}"
                )


# --------------------------------------------------
# 13. RANK LIST
# --------------------------------------------------

if page == "Rank List":
    st.subheader("Trainee Rank List")

    df = load_results()

    if df.empty:
        st.info("No results available for ranking.")
    else:
        # Average percentage across all attempts per roll number.
        rank = (
            df.groupby(["roll_no", "name"], as_index=False)
            .agg(
                Exams_Attempted=("id", "count"),
                Average_Percentage=("percentage", "mean"),
                Best_Percentage=("percentage", "max")
            )
            .sort_values(
                ["Average_Percentage", "Best_Percentage"],
                ascending=False
            )
        )

        rank.insert(0, "Rank", range(1, len(rank) + 1))
        rank["Average_Percentage"] = rank[
            "Average_Percentage"
        ].round(2)

        st.dataframe(rank, use_container_width=True)

        st.download_button(
            "Download Rank List",
            data=rank.to_csv(index=False).encode("utf-8"),
            file_name="copa_rank_list.csv",
            mime="text/csv"
        )


# --------------------------------------------------
# 14. INDIVIDUAL TRAINEE PERFORMANCE BY SUBJECT
# --------------------------------------------------

if page == "Trainee Performance":
    st.subheader("Individual Trainee Performance")
    st.write(
        "Review each trainee's performance across all COPA subjects. "
        "Use subject-wise tests to identify strengths and topics that need more practice."
    )

    all_results = load_results()
    if all_results.empty:
        st.info("No examination results are available yet. Conduct subject-wise tests first.")
    else:
        trainee_options = (
            all_results[["roll_no", "name"]]
            .drop_duplicates()
            .sort_values(["name", "roll_no"])
        )
        trainee_lookup = {
            f"{row['name']} ({row['roll_no']})": row['roll_no']
            for _, row in trainee_options.iterrows()
        }
        selected_label = st.selectbox(
            "Select trainee", list(trainee_lookup.keys()), key="performance_trainee"
        )
        selected_roll = trainee_lookup[selected_label]
        trainee_df = all_results[all_results["roll_no"] == selected_roll].copy()

        attempts = len(trainee_df)
        average_all = float(trainee_df["percentage"].mean())
        best_all = float(trainee_df["percentage"].max())
        subjects_attempted = trainee_df["subject"].nunique()

        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric("Exams Completed", attempts)
        metric2.metric("Subjects Attempted", f"{subjects_attempted} / {len(SUBJECTS)}")
        metric3.metric("Average Percentage", f"{average_all:.1f}%")
        metric4.metric("Best Percentage", f"{best_all:.1f}%")

        # Build one row per configured subject so unattempted subjects are visible too.
        subject_rows = []
        for subject_name in SUBJECTS:
            subject_results = trainee_df[trainee_df["subject"] == subject_name].copy()
            if subject_results.empty:
                subject_rows.append({
                    "Subject": subject_name,
                    "Attempts": 0,
                    "Average %": None,
                    "Best %": None,
                    "Latest Score": "Not attempted",
                    "Latest %": None,
                    "Latest Exam Date": "—",
                    "Status": "Not attempted"
                })
            else:
                subject_results = subject_results.sort_values(
                    ["submitted_at", "id"], ascending=False
                )
                latest = subject_results.iloc[0]
                avg = float(subject_results["percentage"].mean())
                best = float(subject_results["percentage"].max())
                subject_rows.append({
                    "Subject": subject_name,
                    "Attempts": int(len(subject_results)),
                    "Average %": round(avg, 2),
                    "Best %": round(best, 2),
                    "Latest Score": f"{int(latest['score'])} / {int(latest['total'])}",
                    "Latest %": round(float(latest["percentage"]), 2),
                    "Latest Exam Date": str(latest["submitted_at"]),
                    "Status": "Good" if avg >= 60 else "Needs practice"
                })

        performance_df = pd.DataFrame(subject_rows)
        st.markdown("### Subject-wise Performance Summary")
        st.dataframe(performance_df, use_container_width=True, hide_index=True)

        attempted = performance_df[performance_df["Attempts"] > 0].copy()
        if not attempted.empty:
            st.markdown("### Average Percentage by Subject")
            chart_df = attempted[["Subject", "Average %"]].set_index("Subject")
            st.bar_chart(chart_df)

            st.markdown("### Select a Subject for Detailed Review")
            selected_subject = st.selectbox(
                "Subject details", SUBJECTS, key="individual_subject_detail"
            )
            selected_attempts = trainee_df[trainee_df["subject"] == selected_subject].copy()
            if selected_attempts.empty:
                st.info(f"{selected_label} has not attempted {selected_subject} yet.")
            else:
                selected_attempts = selected_attempts.sort_values(
                    ["submitted_at", "id"], ascending=False
                )
                st.markdown("#### Examination Attempts")
                st.dataframe(
                    selected_attempts[["id", "score", "total", "percentage", "submitted_at"]]
                    .rename(columns={
                        "id": "Result ID", "score": "Score", "total": "Total Marks",
                        "percentage": "Percentage", "submitted_at": "Submitted At"
                    }),
                    use_container_width=True,
                    hide_index=True
                )

                latest = selected_attempts.iloc[0]
                try:
                    detail_rows = json.loads(latest["details_json"])
                except (TypeError, json.JSONDecodeError):
                    detail_rows = []
                if detail_rows:
                    detail_df = pd.DataFrame(detail_rows)
                    st.markdown("#### Latest Test: Question-wise Review")
                    st.dataframe(detail_df, use_container_width=True, hide_index=True)
                    if "topic" in detail_df.columns and "is_correct" in detail_df.columns:
                        topic_perf = detail_df.groupby("topic", as_index=False).agg(
                            Questions=("is_correct", "count"),
                            Correct=("is_correct", "sum")
                        )
                        topic_perf["Accuracy %"] = (
                            topic_perf["Correct"] / topic_perf["Questions"] * 100
                        ).round(1)
                        st.markdown("#### Topics to Review")
                        st.dataframe(topic_perf, use_container_width=True, hide_index=True)
                        weak_topics = topic_perf[topic_perf["Accuracy %"] < 60]["topic"].tolist()
                        if weak_topics:
                            st.warning("Suggested topics for more practice: " + ", ".join(weak_topics))
                        else:
                            st.success("Good work! No topic below 60% accuracy in the latest test.")

        st.download_button(
            "Download This Trainee's Subject-wise Report (CSV)",
            data=performance_df.to_csv(index=False).encode("utf-8"),
            file_name=f"trainee_performance_{selected_roll}.csv",
            mime="text/csv"
        )


# --------------------------------------------------
# 15. TOPIC-WISE PERFORMANCE ANALYSIS
# --------------------------------------------------

if page == "Topic Analysis":
    st.subheader("Topic-wise Performance")

    df = load_results()

    if df.empty:
        st.info("Complete an exam before viewing analysis.")
    else:
        subject_filter = st.selectbox(
            "Select subject",
            ["All Subjects"] + SUBJECTS
        )

        topic_rows = []

        for _, row in df.iterrows():
            if (
                subject_filter != "All Subjects"
                and row["subject"] != subject_filter
            ):
                continue

            for d in json.loads(row["details_json"]):
                topic_rows.append({
                    "Subject": row["subject"],
                    "Topic": d["topic"],
                    "Correct": int(d["is_correct"]),
                    "Marks Awarded": d["marks_awarded"],
                    "Marks Available": d.get("marks_available", 1)
                })

        if topic_rows:
            topic_df = pd.DataFrame(topic_rows)

            summary = (
                topic_df.groupby(["Subject", "Topic"], as_index=False)
                .agg(
                    Questions_Attempted=("Topic", "count"),
                    Correct_Answers=("Correct", "sum"),
                    Marks_Awarded=("Marks Awarded", "sum"),
                    Marks_Available=("Marks Available", "sum")
                )
            )

            summary["Accuracy_Percent"] = (
                summary["Correct_Answers"]
                / summary["Questions_Attempted"] * 100
            ).round(2)

            st.dataframe(summary, use_container_width=True)

            chart_data = summary.set_index("Topic")[
                "Accuracy_Percent"
            ]
            st.bar_chart(chart_data)

            st.download_button(
                "Download Topic Analysis",
                data=summary.to_csv(index=False).encode("utf-8"),
                file_name="topic_analysis.csv",
                mime="text/csv"
            )
        else:
            st.info("No topic data is available for this selection.")


# --------------------------------------------------
# 16. QUESTION BANK
# --------------------------------------------------

if page == "Question Bank":
    st.subheader("Question Bank")

    # Bulk import questions from an Excel (.xlsx) or CSV file.
    with st.expander("📥 Import Questions from Excel / CSV", expanded=False):
        st.write(
            "Upload a spreadsheet with columns for Subject, Question, Option A, "
            "Option B, Option C, Option D and Answer. Topic and Marks are optional."
        )
        st.caption(
            "Answer can be A/B/C/D, Option A/Option B/etc., or the exact correct option text."
        )
        uploaded_questions_file = st.file_uploader(
            "Choose Excel or CSV file",
            type=["xlsx", "csv"],
            key="question_bank_bulk_upload",
        )

        if uploaded_questions_file is not None:
            try:
                if uploaded_questions_file.name.lower().endswith(".csv"):
                    try:
                        import_df = pd.read_csv(
                        uploaded_questions_file,
                        encoding="utf-8-sig"
                    )
                    except UnicodeDecodeError:
                        uploaded_questions_file.seek(0)
                        import_df = pd.read_csv(
                        uploaded_questions_file,
                        encoding="cp1252"
                    )
                else:
                    import_df = pd.read_excel(uploaded_questions_file)

                # Match headings without depending on capitalization or extra spaces.
                import_df.columns = [
                    str(col).strip().lower().replace("_", " ")
                    for col in import_df.columns
                ]
                required_columns = [
                    "subject", "question", "option a", "option b",
                    "option c", "option d", "answer"
                ]
                missing_columns = [
                    col for col in required_columns if col not in import_df.columns
                ]

                if missing_columns:
                    st.error(
                        "Missing required column(s): "
                        + ", ".join(missing_columns)
                        + ". Please check your Excel headings."
                    )
                else:
                    st.write("**Preview of your spreadsheet**")
                    st.dataframe(import_df.head(10), use_container_width=True)

                    if st.button(
                        "Check and Import Questions",
                        type="primary",
                        key="run_question_import",
                    ):
                        valid_rows = []
                        invalid_rows = []
                        answer_map = {
                            "a": 0, "option a": 0,
                            "b": 1, "option b": 1,
                            "c": 2, "option c": 2,
                            "d": 3, "option d": 3,
                        }

                        with connect_db() as con:
                            existing = con.execute(
                                "SELECT subject, question FROM questions"
                            ).fetchall()
                            existing_keys = {
                                (str(subj).strip().casefold(),
                                 str(q).strip().casefold())
                                for subj, q in existing
                            }

                            for row_index, row in import_df.iterrows():
                                excel_row = row_index + 2
                                subject = str(row.get("subject", "")).strip()
                                question = str(row.get("question", "")).strip()
                                topic_value = row.get("topic", "General")
                                topic = (
                                    "General" if pd.isna(topic_value)
                                    or not str(topic_value).strip()
                                    else str(topic_value).strip()
                                )
                                option_values = [
                                    row.get("option a"), row.get("option b"),
                                    row.get("option c"), row.get("option d")
                                ]
                                options = [
                                    "" if pd.isna(value) else str(value).strip()
                                    for value in option_values
                                ]
                                answer_value = row.get("answer")
                                answer_text = (
                                    "" if pd.isna(answer_value)
                                    else str(answer_value).strip()
                                )

                                errors = []
                                if not subject or subject.casefold() == "nan":
                                    errors.append("Subject is empty")
                                elif subject not in SUBJECTS:
                                    errors.append(
                                        "Subject must be one of: " + ", ".join(SUBJECTS)
                                    )
                                if not question or question.casefold() == "nan":
                                    errors.append("Question is empty")
                                if any(not opt for opt in options):
                                    errors.append("One or more options are empty")
                                elif len({opt.casefold() for opt in options}) != 4:
                                    errors.append("Options must be different")

                                answer_index = answer_map.get(answer_text.casefold())
                                if answer_index is None:
                                    matches = [
                                        i for i, opt in enumerate(options)
                                        if opt.casefold() == answer_text.casefold()
                                    ]
                                    if len(matches) == 1:
                                        answer_index = matches[0]
                                    else:
                                        errors.append(
                                            "Answer must be A/B/C/D or match an option exactly"
                                        )

                                marks_value = row.get("marks", 1)
                                try:
                                    marks = 1 if pd.isna(marks_value) else int(marks_value)
                                    if marks < 1 or marks > 10:
                                        raise ValueError
                                except (ValueError, TypeError, OverflowError):
                                    marks = 1
                                    errors.append("Marks must be a whole number from 1 to 10")

                                key = (subject.casefold(), question.casefold())
                                if key in existing_keys:
                                    errors.append("Duplicate question already in the bank")

                                if errors:
                                    invalid_rows.append({
                                        "Excel Row": excel_row,
                                        "Question": question[:100],
                                        "Problem": "; ".join(errors),
                                    })
                                    continue

                                valid_rows.append((
                                    subject, topic, question, json.dumps(options),
                                    options[answer_index], marks
                                ))
                                # Also prevent duplicates within the same uploaded file.
                                existing_keys.add(key)

                            if valid_rows:
                                con.executemany("""
                                    INSERT INTO questions (
                                        subject, topic, question, options_json,
                                        correct_answer, marks
                                    ) VALUES (?, ?, ?, ?, ?, ?)
                                """, valid_rows)

                        if valid_rows:
                            st.success(
                                f"Successfully imported {len(valid_rows)} question(s)."
                            )
                        else:
                            st.warning("No questions were imported.")

                        if invalid_rows:
                            st.warning(
                                f"{len(invalid_rows)} row(s) were skipped. "
                                "Correct these rows in Excel and upload again."
                            )
                            st.dataframe(
                                pd.DataFrame(invalid_rows),
                                use_container_width=True,
                            )

            except Exception as exc:
                st.error(
                    "Could not read this file. Please check that it is a valid "
                    f"Excel or CSV file. Details: {exc}"
                )

    with connect_db() as con:
        bank = pd.read_sql_query("""
            SELECT id, subject, topic, question, options_json,
                   correct_answer, marks
            FROM questions
            ORDER BY subject, topic, id
        """, con)

    if not bank.empty:
        view = bank.copy()
        view["options"] = view["options_json"].apply(
            lambda x: ", ".join(json.loads(x))
        )
        view = view.drop(columns=["options_json"])
        st.dataframe(view, use_container_width=True)

        st.markdown("### Edit or Delete a Question")
        question_rows = bank.to_dict("records")
        question_labels = {
            f"ID {row['id']} | {row['subject']} | {str(row['question'])[:90]}": row
            for row in question_rows
        }
        selected_label = st.selectbox(
            "Select a question",
            options=list(question_labels.keys()),
            key="manage_question_selection",
        )
        selected_question = question_labels[selected_label]
        selected_options = json.loads(selected_question["options_json"])
        option_labels = ["Option A", "Option B", "Option C", "Option D"]
        current_answer_index = (
            selected_options.index(selected_question["correct_answer"])
            if selected_question["correct_answer"] in selected_options else 0
        )

        with st.form("edit_question_form"):
            edit_subject = st.selectbox(
                "Subject", SUBJECTS,
                index=SUBJECTS.index(selected_question["subject"])
                if selected_question["subject"] in SUBJECTS else 0,
                key="edit_subject",
            )
            edit_topic = st.text_input(
                "Topic", value=selected_question["topic"], key="edit_topic"
            )
            edit_question = st.text_area(
                "Question", value=selected_question["question"], key="edit_question"
            )
            edit_a = st.text_input("Option A", value=selected_options[0], key="edit_option_a")
            edit_b = st.text_input("Option B", value=selected_options[1], key="edit_option_b")
            edit_c = st.text_input("Option C", value=selected_options[2], key="edit_option_c")
            edit_d = st.text_input("Option D", value=selected_options[3], key="edit_option_d")
            edit_options = [edit_a, edit_b, edit_c, edit_d]
            edit_answer_label = st.selectbox(
                "Correct answer",
                option_labels,
                index=current_answer_index,
                format_func=lambda label: f"{label}: {edit_options[option_labels.index(label)]}",
                key="edit_correct_answer",
            )
            edit_marks = st.number_input(
                "Marks", min_value=1, max_value=10,
                value=max(1, min(10, int(selected_question["marks"]))),
                key="edit_marks",
            )
            save_edit = st.form_submit_button("💾 Save Changes")

        if save_edit:
            if not edit_topic.strip() or not edit_question.strip() or any(not x.strip() for x in edit_options):
                st.error("Please complete all question fields before saving.")
            elif len(set(edit_options)) != 4:
                st.error("Please enter four different options.")
            else:
                correct = edit_options[option_labels.index(edit_answer_label)]
                with connect_db() as con:
                    con.execute("""
                        UPDATE questions
                        SET subject = ?, topic = ?, question = ?, options_json = ?,
                            correct_answer = ?, marks = ?
                        WHERE id = ?
                    """, (
                        edit_subject, edit_topic.strip(), edit_question.strip(),
                        json.dumps(edit_options), correct, int(edit_marks),
                        int(selected_question["id"]),
                    ))
                st.success("Question updated successfully.")
                st.rerun()

        with st.expander("🗑️ Delete this question"):
            st.warning("Deleting a question removes it from the question bank. Existing examination results are not changed.")
            confirm_delete = st.checkbox(
                f"I confirm that I want to delete question ID {selected_question['id']}",
                key=f"confirm_delete_{selected_question['id']}",
            )
            if st.button(
                "Delete Selected Question",
                type="primary",
                disabled=not confirm_delete,
                key=f"delete_question_{selected_question['id']}",
            ):
                with connect_db() as con:
                    con.execute(
                        "DELETE FROM questions WHERE id = ?",
                        (int(selected_question["id"]),),
                    )
                st.success("Question deleted successfully.")
                st.rerun()
    else:
        st.info("The question bank is empty. Add a question below to get started.")

    st.markdown("### Add a New Question")

    with st.form("add_question_form"):
        new_subject = st.selectbox(
            "Subject", SUBJECTS, key="new_subject"
        )
        new_topic = st.text_input("Topic")
        new_question = st.text_area("Question")
        option_a = st.text_input("Option A")
        option_b = st.text_input("Option B")
        option_c = st.text_input("Option C")
        option_d = st.text_input("Option D")

        new_options = [option_a, option_b, option_c, option_d]
        new_answer = st.selectbox(
            "Correct answer",
            ["Option A", "Option B", "Option C", "Option D"]
        )
        new_marks = st.number_input(
            "Marks", min_value=1, max_value=10, value=1
        )

        add = st.form_submit_button("Save Question")

    if add:
        if (
            not new_topic.strip()
            or not new_question.strip()
            or any(not x.strip() for x in new_options)
        ):
            st.error("Please complete all question fields.")
        elif len(set(new_options)) != 4:
            st.error("Please enter four different options.")
        else:
            correct = new_options[
                ["Option A", "Option B", "Option C", "Option D"]
                .index(new_answer)
            ]

            with connect_db() as con:
                con.execute("""
                    INSERT INTO questions (
                        subject, topic, question, options_json,
                        correct_answer, marks
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    new_subject,
                    new_topic.strip(),
                    new_question.strip(),
                    json.dumps(new_options),
                    correct,
                    int(new_marks)
                ))

            st.success("Question saved to the database.")
            st.rerun()

st.divider()
st.caption("COPA Online Examination System | Educational project")
