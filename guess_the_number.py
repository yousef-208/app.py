import streamlit as st
from google.oauth2 import service_account
# If you use Google APIs, ensure you have `google-auth` (and the specific client) in requirements.txt

# Load service account info from secrets TOML
sa_info = dict(st.secrets["google_service_account"])

# Create Credentials object
credentials = service_account.Credentials.from_service_account_info(sa_info)

# Example: use credentials with a Google client (e.g., Google Cloud Storage)
# from google.cloud import storage
# client = storage.Client(credentials=credentials, project=sa_info["project_id"])


# Custom CSS for colors
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
if "leaderboard" not in st.session_state:
    st.session_state.leaderboard = []

st.markdown(f"<h3 style='color:#008080;'>I'm thinking of a number between 1 and {max_num}. You have {st.session_state.max_attempts} tries!</h3>", unsafe_allow_html=True)

# User input
guess = st.number_input("🎲 Enter your guess:", min_value=1, max_value=max_num, step=1)

if st.button("✅ Submit Guess"):
    if not name:
        st.error("Please enter your name before playing!")
    else:
        st.session_state.attempts += 1
        if guess < st.session_state.number_to_guess:
            st.warning("📉 Too low! Try again.")
        elif guess > st.session_state.number_to_guess:
            st.warning("📈 Too high! Try again.")
        else:
            st.success(f"🎉 Correct! The number was {st.session_state.number_to_guess}.")
            st.balloons()
            # Save score to leaderboard
            st.session_state.leaderboard.append({"name": name, "attempts": st.session_state.attempts})
            st.session_state.leaderboard = sorted(st.session_state.leaderboard, key=lambda x: x["attempts"])
            st.session_state.number_to_guess = random.randint(1, max_num)
            st.session_state.attempts = 0

        # Check attempts
        if st.session_state.attempts >= st.session_state.max_attempts and guess != st.session_state.number_to_guess:
            st.error(f"😢 Out of tries! The number was {st.session_state.number_to_guess}.")
            st.write("🔄 Click below to play again.")
            if st.button("Restart Game"):
                st.session_state.number_to_guess = random.randint(1, max_num)
                st.session_state.attempts = 0

# Display leaderboard
st.subheader("🏆 Leaderboard")
if st.session_state.leaderboard:
    for i, entry in enumerate(st.session_state.leaderboard[:10], start=1):
        st.write(f"{i}. {entry['name']} - {entry['attempts']} attempts")
else:
    st.write("No scores yet. Be the first!")



