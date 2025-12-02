
import random
import os
import streamlit as st
from datetime import datetime
from google.oauth2 import service_account

# --- NEW: Google Sheets (gspread) ---
import gspread

# ===============================
# Google Sheets setup & helpers
# ===============================

# Scopes needed for Sheets + (optional) Drive create
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Load service account from Streamlit secrets (must be the full JSON object)
sa_info = dict(st.secrets["google_service_account"])

# Build credentials with required scopes
credentials = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)

# gspread client
gc = gspread.authorize(credentials)

# Config: sheet name or id (optional)
SPREADSHEET_NAME = st.secrets.get("gsheet_name", "GuessTheNumberLeaderboard")
SPREADSHEET_ID = st.secrets.get("gsheet_id", None)  # if you prefer opening by key

def get_worksheet():
    """
    Open the leaderboard spreadsheet (by ID if provided; otherwise by name),
    create it if missing, ensure a header row, and return the first worksheet.
    """
    try:
        if SPREADSHEET_ID:
            sh = gc.open_by_key(SPREADSHEET_ID)
        else:
            # Try open by name; create if not found
            try:
                sh = gc.open(SPREADSHEET_NAME)
            except gspread.SpreadsheetNotFound:
                sh = gc.create(SPREADSHEET_NAME)
    except Exception as e:
        st.error(
            f"Could not access the Google Sheet. Please ensure the service account "
            f"has permission. Error: {e}"
        )
        st.stop()

    ws = sh.sheet1  # use first worksheet
    # Ensure header row exists
    header = ws.row_values(1)
    expected_header = ["name", "attempts", "timestamp"]
    if header != expected_header:
        ws.clear()
        ws.append_row(expected_header)
    return ws

worksheet = get_worksheet()

def add_score(name: str, attempts: int):
    """Append a score row to the sheet."""
    ts = datetime.utcnow().isoformat(timespec="seconds")
    worksheet.append_row([name, int(attempts), ts])

@st.cache_data(ttl=30)
def load_leaderboard(limit=10):
    """
    Fetch all records from the sheet, sort by attempts ascending, then timestamp,
    and return top N. Cached for 30s to avoid hitting API constantly.
    """
    records = worksheet.get_all_records()  # [{'name':..., 'attempts':..., 'timestamp':...}, ...]
    # Defensive: ensure attempts are ints
    for r in records:
        try:
            r["attempts"] = int(r.get("attempts", 0))
        except Exception:
            r["attempts"] = 0
    sorted_records = sorted(records, key=lambda x: (x["attempts"], x.get("timestamp", "")))
    return sorted_records[:limit]

# ===============================
# UI: Styling
# ===============================
st.markdown("""
    <style>
    .main {
        background-color: #f0f8ff;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-size: 18px;
        border-radius: 10px;
        padding: 10px 20px;
    }
    .stRadio>div {
        color: #ff4500;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.markdown("<h1 style='text-align:center; color:#ff1493;'>🎯 Guess the Number Game 🎯</h1>", unsafe_allow_html=True)

# Player info
st.subheader("👤 Player Information")
name = st.text_input("Enter your name:")

# Difficulty selection
difficulty = st.radio("🔥 Choose a difficulty level:", ["Easy (1-50)", "Hard (1-100)"])
max_num = 50 if "Easy" in difficulty else 100

# Initialize session state
if "number_to_guess" not in st.session_state:
    st.session_state.number_to_guess = random.randint(1, max_num)
    st.session_state.attempts = 0
    st.session_state.max_attempts = 10

# Helpful message
st.markdown(
    f"<h3 style='color:#008080;'>I'm thinking of a number between 1 and {max_num}. "
    f"You have {st.session_state.max_attempts} tries!</h3>",
    unsafe_allow_html=True
)

# Guess input
guess = st.number_input("🎲 Enter your guess:", min_value=1, max_value=max_num, step=1)

# Separate restart button so it's always accessible
restart = st.button("🔄 Restart Game")

if restart:
    st.session_state.number_to_guess = random.randint(1, max_num)
    st.session_state.attempts = 0
    st.info("Game restarted! A new number has been chosen.")

# Submit Guess
if st.button("✅ Submit Guess"):
    if not name:
        st.error("Please enter your name before playing!")
    else:
        st.session_state.attempts += 1
        target = st.session_state.number_to_guess

        if guess < target:
            st.warning("📉 Too low! Try again.")
        elif guess > target:
            st.warning("📈 Too high! Try again.")
        else:
            st.success(f"🎉 Correct! The number was {target}.")
            st.balloons()
            # --- NEW: Persist score to Google Sheets ---
            add_score(name, st.session_state.attempts)

            # Reset for next round
            st.session_state.number_to_guess = random.randint(1, max_num)
            st.session_state.attempts = 0

        # Out of tries
        if st.session_state.attempts >= st.session_state.max_attempts and guess != target:
            st.error(f"😢 Out of tries! The number was {target}.")
            st.info("Click 'Restart Game' to play again.")

# Display leaderboard
st.subheader("🏆 Leaderboard (Global)")
top10 = load_leaderboard(limit=10)
if top10:
    # Show as a nicely formatted table
    # Add rank
    for i, row in enumerate(top10, start=1):
        st.write(f"{i}. {row['name']} - {row['attempts']} attempts  ⏱ {row.get('timestamp','')}")
else:
    st.write("No scores yet. Be the first!")

       



