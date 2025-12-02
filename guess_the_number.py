import random
import streamlit as st
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ===============================
# Google Sheets Setup (Sheets API ONLY)
# ===============================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


# Load credentials from secrets
if "google_service_account" not in st.secrets:
    st.error("Missing [google_service_account] in Secrets. Please add your service account JSON in Streamlit Secrets.")
    st.stop()

sa_info = dict(st.secrets["google_service_account"])

# 🔧 Normalize private key formatting to avoid binascii errors
pk = sa_info.get("private_key", "")
if pk:
    sa_info["private_key"] = pk.replace("\\n", "\n")

credentials = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)

# Build Sheets API client
service = build("sheets", "v4", credentials=credentials)

# Build Sheets API client
service = build("sheets", "v4", credentials=credentials)

# Get Sheet ID: prefer Secrets; allow manual input fallback
SPREADSHEET_ID = st.secrets.get("gsheet_id", None)

with st.expander("📄 Google Sheets configuration", expanded=False):
    st.write("This app uses Google Sheets API only (no Drive API).")
    st.write({
        "has_gsheet_id_secret": bool(SPREADSHEET_ID),
        "service_account_email": sa_info.get("client_email", "unknown"),
    })

if not SPREADSHEET_ID:
    st.warning("No `gsheet_id` found in Secrets. Paste your Sheet ID below to continue.")
    user_sheet_id = st.text_input(
        "Google Sheet ID",
        help="The long ID from the URL: https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit",
        placeholder="1vw6e-z0AJKlDyE5oytQWcBH-iAe2HCZ8uhSPKyZXUgs",
    )
    if user_sheet_id:
        SPREADSHEET_ID = user_sheet_id
    else:
        st.stop()

RANGE_NAME = "Sheet1"  # Change if your tab name differs (e.g., 'Leaderboard')

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
    # Expect header: name | attempts | timestamp
    records = []
    for r in rows[1:]:
        # be defensive about missing cells
        name = r[0] if len(r) > 0 else ""
        attempts_str = r[1] if len(r) > 1 else "0"
        ts = r[2] if len(r) > 2 else ""
        try:
            attempts = int(attempts_str)
        except:
            attempts = 0
        records.append({"name": name, "attempts": attempts, "timestamp": ts})
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
