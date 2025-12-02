
import random
import streamlit as st
from datetime import datetime
from google.oauth2 import service_account
import gspread

# ===============================
# Google Sheets Setup
# ===============================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Load service account credentials from Streamlit Secrets
sa_info = dict(st.secrets["google_service_account"])
credentials = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)

# Authorize gspread
gc = gspread.authorize(credentials)

# Spreadsheet name or ID
SPREADSHEET_NAME = "GuessTheNumberLeaderboard"

def get_worksheet():
    """Open or create the leaderboard sheet and ensure header row exists."""
    try:
        try:
            sh = gc.open(SPREADSHEET_NAME)
        except gspread.SpreadsheetNotFound:
            sh = gc.create(SPREADSHEET_NAME)
        ws = sh.sheet1
        header = ws.row_values(1)
        expected_header = ["name", "attempts", "timestamp"]
        if header != expected_header:
            ws.clear()
            ws.append_row(expected_header)
        return ws
    except Exception as e:
        st.error(f"Could not access Google Sheet. Error: {e}")
        st.stop()

worksheet = get_worksheet()

def add_score(name: str, attempts: int):
    """Append a score to the Google Sheet."""
    ts = datetime.utcnow().isoformat(timespec="seconds")
    worksheet.append_row([name, int(attempts), ts])

@st.cache_data(ttl=30)
def load_leaderboard(limit=10):
    """Fetch and sort leaderboard from Google Sheets."""
    records = worksheet.get_all_records()
    for r in records:
        try:
            r["attempts"] = int(r.get("attempts", 0))
        except:
            r["attempts"] = 0
    sorted_records = sorted(records, key=lambda x: (x["attempts"], x.get("timestamp", "")))
    return sorted_records[:limit]

# ===============================
# UI Styling
# ===============================
st.markdown("""
    <style>
    .main { background-color: #f0f8ff; }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-size: 18px;
        border-radius: 10px;
        padding: 10px 20px;
    }
    .stRadio>div { color: #ff4500; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ===============================
# Game Logic
# ===============================
st.markdown("<h1 style='text-align:center; color:#ff1493;'>🎯 Guess the Number Game 🎯</h1>", unsafe_allow_html=True)

st.subheader("👤 Player Information")
name = st.text_input("Enter your name:")

difficulty = st.radio("🔥 Choose a difficulty level:", ["Easy (1-50)", "Hard (1-100)"])
max_num = 50 if "Easy" in difficulty else 100

if "number_to_guess" not in st.session_state:
    st.session_state.number_to_guess = random.randint(1, max_num)
    st.session_state.attempts = 0
    st.session_state.max_attempts = 10

st.markdown(f"<h3 style='color:#008080;'>I'm thinking of a number between 1 and {max_num}. You have {st.session_state.max_attempts} tries!</h3>", unsafe_allow_html=True)

guess = st.number_input("🎲 Enter your guess:", min_value=1, max_value=max_num, step=1)

if st.button("🔄 Restart Game"):
    st.session_state.number_to_guess = random.randint(1, max_num)
    st.session_state.attempts = 0
    st.info("Game restarted! A new number has been chosen.")

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
            add_score(name, st.session_state.attempts)
            load_leaderboard.clear()  # Refresh cache
            st.session_state.number_to_guess = random.randint(1, max_num)
            st.session_state.attempts = 0

        if st.session_state.attempts >= st.session_state.max_attempts and guess != target:
            st.error(f"😢 Out of tries! The number was {target}.")
            st.info("Click 'Restart Game' to play again.")

# ===============================
# Leaderboard Display
# ===============================
st.subheader("🏆 Global Leaderboard")
top10 = load_leaderboard(limit=10)
if top10:
    for i, row in enumerate(top10, start=1):
        st.write(f"{i}. {row['name']} - {row['attempts']} attempts ⏱ {row.get('timestamp','')}")
else:
    st.write("No scores yet. Be the first!")
