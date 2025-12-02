
import random
import streamlit as st
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import gspread

# ===============================
# Google Sheets Setup
# ===============================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- Load & validate secrets ---
if "google_service_account" not in st.secrets:
    st.error("Missing [google_service_account] section in secrets.toml.")
    st.stop()

sa_info = dict(st.secrets["google_service_account"])  # make a mutable copy

required_fields = ["client_email", "token_uri", "private_key", "gsheet_id"]
missing = [f for f in required_fields if not sa_info.get(f)]
if missing:
    st.error(f"Missing required fields in secrets: {missing}")
    st.stop()

# Normalize private key BEFORE creating credentials
pk = sa_info["private_key"].strip()

# Handle both cases:
# - If secrets has escaped \n (common), convert to real newlines
# - If secrets already contains real newlines, leave them
if "\\n" in pk and "\n" not in pk:
    pk = pk.replace("\\n", "\n")

sa_info["private_key"] = pk

# Sanity checks for key shape without revealing content
if "..." in pk:
    st.error("Your private_key contains '...'. Paste the FULL key from the JSON. Do not use ellipses.")
    st.stop()
if not pk.startswith("-----BEGIN PRIVATE KEY-----") or "-----END PRIVATE KEY-----" not in pk:
    st.error("Private key must include the PEM header/footer: BEGIN/END PRIVATE KEY.")
    st.stop()
if len(pk) < 1200:  # Typical PKCS#8 service account keys are ~1600–1800 chars
    st.error("Private key appears too short. Paste the complete value from your Google Cloud JSON file.")
    st.stop()

# Create credentials (catch ASN.1 parse issues explicitly)
try:
    credentials = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)
except Exception as e:
    st.error(f"Failed to parse service account credentials. Root cause: {e}")
    st.stop()

# Connect to Google Sheets
try:
    client = gspread.authorize(credentials)
except Exception as e:
    st.warning(f"gspread authorization warning (not fatal for Sheets API usage): {e}")

# Build Sheets API client
try:
    service = build("sheets", "v4", credentials=credentials)
except Exception as e:
    st.error(f"Failed to build Sheets API client: {e}")
    st.stop()

# Spreadsheet details
SPREADSHEET_ID = sa_info["gsheet_id"]
RANGE_NAME = "Sheet1"  # Change if your tab name differs (e.g., 'Leaderboard')

def add_score(name: str, attempts: int):
    """Append a score to the Google Sheet."""
    ts = datetime.utcnow().isoformat(timespec="seconds")
    values = [[name, str(attempts), ts]]
    body = {"values": values}
    try:
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
    except Exception as e:
        st.error(f"Failed to append to the sheet: {e}")

@st.cache_data(ttl=30)
def load_leaderboard(limit=10):
    """Fetch and sort leaderboard from Google Sheets."""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME
        ).execute()
    except Exception as e:
        st.error(f"Failed to read from the sheet: {e}")
        return []

    rows = result.get("values", [])
    if len(rows) <= 1:
        return []
    records = []
    for r in rows[1:]:
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

# Reset the number when difficulty changes
if "last_max_num" not in st.session_state or st.session_state.last_max_num != max_num:
    st.session_state.number_to_guess = random.randint(1, max_num)
    st.session_state.attempts = 0
    st.session_state.max_attempts = 10
    st.session_state.last_max_num = max_num

st.markdown(
    f"<h3 style='color:#008080;'>I'm thinking of a number between 1 and {max_num}. You have {st.session_state.max_attempts} tries!</h3>",
    unsafe_allow_html=True
)

guess = st.number_input("🎲 Enter your guess:", min_value=1, max_value=max_num, step=1)

col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 Restart Game"):
        st.session_state.number_to_guess = random.randint(1, max_num)
        st.session_state.attempts = 0
        st.info("Game restarted! A new number has been chosen.")

with col2:
    if st.button("✅ Submit Guess"):
        if not name.strip():
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
                add_score(name.strip(), st.session_state.attempts)
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
