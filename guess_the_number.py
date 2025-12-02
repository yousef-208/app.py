
import random
import streamlit as st
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ===============================
# Google Sheets Setup
# ===============================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
sa_info = dict(st.secrets["google_service_account"])
credentials = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)

# Build Sheets API client
service = build("sheets", "v4", credentials=credentials)

SPREADSHEET_ID = st.secrets["gsheet_id"]
RANGE_NAME = "Sheet1"  # Assuming your sheet is named "Sheet1"

def add_score(name: str, attempts: int):
    """Append a score to the Google Sheet."""
    ts = datetime.utcnow().isoformat(timespec="seconds")
    values = [[name, str(attempts), ts]]
    body = {"values": values}
    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

@st.cache_data(ttl=30)
def load_leaderboard(limit=10):
    """Fetch and sort leaderboard from Google Sheets."""
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME
    ).execute()
    rows = result.get("values", [])
    if len(rows) <= 1:
        return []
    records = [{"name": r[0], "attempts": int(r[1]), "timestamp": r[2]} for r in rows[1:]]
    sorted_records = sorted(records, key=lambda x: (x["attempts"], x["timestamp"]))
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
        st.write(f"{i}. {row['name']} - {row['attempts']} attempts ⏱ {row['timestamp']}")
else:
    st.write("No scores yet. Be the first!")
