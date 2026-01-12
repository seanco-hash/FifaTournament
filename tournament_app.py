import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import os
import json

# --- Configuration ---
# We define the initial data here. If the Sheet is empty, we will bootstrap it with this.
INITIAL_PLAYERS = [
    "Liron Levran", "Itai Eldar", "Amit Azoulay", "Sean Cohen", "Benny Bain", "Yuval Gabay",
    "Naveh Ayal", "Gilad Ben Uziahu", "Ofir Liba", "Omer Mar Chaim", "Sagi Katzav", "Yonatan Golick",
    "Avishay Hadar", "Elie Zemmour", "Amnon Shapiro", "Eyal Hanania", "Sharon Magril", "Neta Kakon",
    "Michael Bubis", "Daniel Arkushin", "Daniel Ben Moshe", "Nadav Kirsch"
]

# We need the fixtures list to initialize the DB if it's empty
INITIAL_MATCHES = [
    {"week": 1, "match_id": 1, "p1": "Liron Levran", "p2": "Itai Eldar"},
    {"week": 1, "match_id": 2, "p1": "Amit Azoulay", "p2": "Sean Cohen"},
    {"week": 1, "match_id": 3, "p1": "Benny Bain", "p2": "Yuval Gabay"},
    {"week": 1, "match_id": 4, "p1": "Naveh Ayal", "p2": "Gilad Ben Uziahu"},
    {"week": 1, "match_id": 5, "p1": "Ofir Liba", "p2": "Omer Mar Chaim"},
    {"week": 1, "match_id": 6, "p1": "Sagi Katzav", "p2": "Yonatan Golick"},
    {"week": 1, "match_id": 7, "p1": "Avishay Hadar", "p2": "Elie Zemmour"},
    # ... (I've truncated the list for brevity, but the logic handles whatever is in the DB)
    # The app will actually load whatever is in the sheet, so the initial list here is just for the very first setup.
    # If you want to force-reset, you can clear the Google Sheet columns manually.
]

TOP_TEAMS = sorted([
    # --- Top Clubs ---
    "Manchester City", "Real Madrid", "Bayern Munich", "Liverpool", "Arsenal",
    "Inter Milan", "Bayer Leverkusen", "Paris Saint-Germain", "FC Barcelona",
    "Atletico Madrid", "Juventus", "Borussia Dortmund", "AC Milan", "RB Leipzig",
    "Atalanta", "Benfica", "Sporting CP", "Napoli", "Tottenham Hotspur",
    "Chelsea", "Manchester United", "Newcastle United", "Aston Villa", "Sevilla",
    "AS Roma", "Lazio", "PSV Eindhoven", "Feyenoord", "Galatasaray", "Ajax",
    "FC Porto",

    # --- Top National Teams ---
    "Argentina", "France ", "England ",
    "Brazil ", "Spain ", "Portugal ",
    "Netherlands ", "Belgium ", "Italy ",
    "Germany ", "Croatia ", "Uruguay ", "Norway ",
])


# --- Helper Functions ---

def get_connection():
    """Establishes the connection to Google Sheets."""
    return st.connection("gsheets", type=GSheetsConnection)


def load_data():
    """Loads match and player data from Google Sheets."""
    conn = get_connection()

    try:
        # Read the 'matches' worksheet
        # ttl=0 ensures we don't cache data, so we always see updates from other users
        df_matches = conn.read(worksheet="Matches", ttl=0)
        df_players = conn.read(worksheet="Players", ttl=0)

        # Check if empty (fresh sheet)
        if df_matches.empty or df_players.empty:
            return None  # Signal that we need to initialize

        # Convert DataFrames back to our app's list-of-dicts format
        matches = df_matches.to_dict(orient="records")
        players = df_players["name"].tolist()

        # Cleanup: Pandas turns None into NaN. We need None for our logic.
        for m in matches:
            for key in ['score1', 'score2', 'team1', 'team2']:
                if pd.isna(m.get(key)):
                    m[key] = None
                elif key in ['score1', 'score2']:
                    m[key] = int(m[key])  # Ensure scores are integers

        return {"matches": matches, "players": players}

    except Exception:
        # If worksheet doesn't exist yet
        return None


def save_data(data):
    """Writes the current state back to Google Sheets."""
    conn = get_connection()

    # Convert matches to DataFrame
    df_matches = pd.DataFrame(data["matches"])
    df_players = pd.DataFrame({"name": data["players"]})

    # Write to Sheets (update overwrites the data in the sheet)
    conn.update(worksheet="Matches", data=df_matches)
    conn.update(worksheet="Players", data=df_players)
    st.cache_data.clear()  # Clear cache to force reload next time


def initialize_sheet():
    """Bootstraps the Google Sheet with initial fixtures."""
    # Create the full fixture list properly (combining your provided fixtures with the JSON structure)
    # For simplicity, if the sheet is empty, I'll assume we need to load the full fixture list provided previously.
    # To keep this code short, I will load a minimal set or rely on the user to 'Reset' using the button.
    # But for a great UX, let's load the full list we created in the previous turn.

    # Re-creating the full fixture list from your previous prompt to ensure it's there on first load
    # (Compressed version for this code block - you can paste the full list from the previous step here if needed)
    # NOTE: In a real scenario, paste the FULL 'matches' list from the previous JSON step into INITIAL_MATCHES below.

    full_matches = [
        {"week": 1, "match_id": 1, "group": "A vs B", "p1": "Liron Levran", "score1": None, "p2": "Itai Eldar",
         "score2": None},
        {"week": 1, "match_id": 2, "group": "A vs B", "p1": "Amit Azoulay", "score1": None, "p2": "Sean Cohen",
         "score2": None},
        # ... You should paste the COMPLETE list from the JSON I gave you earlier here ...
        # If you don't paste it, the app will start empty.
        # For now, I will create a placeholder.
    ]

    # If we are initializing, we use the hardcoded list above or the one from the file
    # For this response, I'll assume the user uses the "Reset" button to load the JSON file logic
    # or we can just save the empty structure and let them add it.
    # BETTER OPTION: Just return an empty structure and let the UI handle it.
    pass


def get_used_teams(data, player_name):
    used = set()
    for m in data["matches"]:
        if m['p1'] == player_name and m.get('team1'): used.add(m['team1'])
        if m['p2'] == player_name and m.get('team2'): used.add(m['team2'])
    return used


def calculate_leaderboard(data):
    players = data["players"]
    matches = data["matches"]
    stats = {p: {'GP': 0, 'W': 0, 'D': 0, 'L': 0, 'GF': 0, 'GA': 0, 'GD': 0, 'Pts': 0} for p in players}

    for m in matches:
        if m.get('score1') is None or m.get('score2') is None: continue
        p1, s1 = m['p1'], m['score1']
        p2, s2 = m['p2'], m['score2']

        # Add to stats if player exists (safety check)
        if p1 in stats:
            stats[p1]['GP'] += 1;
            stats[p1]['GF'] += s1;
            stats[p1]['GA'] += s2;
            stats[p1]['GD'] += (s1 - s2)
        if p2 in stats:
            stats[p2]['GP'] += 1;
            stats[p2]['GF'] += s2;
            stats[p2]['GA'] += s1;
            stats[p2]['GD'] += (s2 - s1)

        if s1 > s2:
            if p1 in stats: stats[p1]['W'] += 1; stats[p1]['Pts'] += 3
            if p2 in stats: stats[p2]['L'] += 1
        elif s2 > s1:
            if p2 in stats: stats[p2]['W'] += 1; stats[p2]['Pts'] += 3
            if p1 in stats: stats[p1]['L'] += 1
        else:
            if p1 in stats: stats[p1]['D'] += 1; stats[p1]['Pts'] += 1
            if p2 in stats: stats[p2]['D'] += 1; stats[p2]['Pts'] += 1

    df = pd.DataFrame.from_dict(stats, orient='index')
    if not df.empty:
        df = df.sort_values(by=['Pts', 'GD', 'GF'], ascending=False)
        df = df.reset_index().rename(columns={'index': 'Player'})
        df.index += 1
    return df


# --- App Layout ---
st.set_page_config(page_title="🏆 FIFA Manager", layout="wide")
st.title("🏆 FIFA Tournament Manager")

# Try to load data
data = load_data()

# --- First Run / Bootstrap Logic ---
if data is None:
    st.warning("⚠️ Database not found or empty. Please initialize the database.")
    # Here we offer to load the initial JSON data you had
    # We will assume 'tournament_data.json' might still exist locally to help bootstrap
    if st.button("🚀 Initialize Database from Local JSON"):
        if os.path.exists('tournament_data.json'):
            with open('tournament_data.json', 'r') as f:
                local_data = json.load(f)
            save_data(local_data)  # Save local JSON content to Google Sheet
            st.success("Database Initialized! Please refresh.")
            st.rerun()
        else:
            st.error("local 'tournament_data.json' not found. Cannot bootstrap.")
    st.stop()  # Stop execution until initialized

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Connected to Google Sheets 🟢")

# --- Main Tabs ---
tab1, tab2, tab3 = st.tabs(["🥇 Leaderboard", "⚽ Enter Scores", "🛡️ Team Tracker"])

# TAB 1: Leaderboard
with tab1:
    st.subheader("Live Standings")
    df = calculate_leaderboard(data)
    st.dataframe(df, use_container_width=True, height=600)

# TAB 2: Enter Scores
with tab2:
    st.subheader("Match Schedule")
    matches = data["matches"]

    unique_weeks = sorted(list(set(m.get('week', 0) for m in matches)))

    for week in unique_weeks:
        week_matches = [m for m in matches if m.get('week') == week]
        is_completed = all(m.get('score1') is not None for m in week_matches)
        title_icon = "✅" if is_completed else "📅"

        with st.expander(f"{title_icon} Week {week}", expanded=True):
            for match in week_matches:
                c_home, c_t1, c_s1, c_sep, c_s2, c_t2, c_away, c_btn = st.columns([2, 2, 0.8, 0.4, 0.8, 2, 2, 1])

                # Data Prep
                val_s1 = int(match['score1']) if match['score1'] is not None else 0
                val_s2 = int(match['score2']) if match['score2'] is not None else 0
                current_t1 = match.get('team1')
                current_t2 = match.get('team2')

                # Used Teams Logic
                used_p1 = get_used_teams(data, match['p1'])
                if current_t1 in used_p1: used_p1.remove(current_t1)

                used_p2 = get_used_teams(data, match['p2'])
                if current_t2 in used_p2: used_p2.remove(current_t2)

                opts_p1 = sorted([t for t in TOP_TEAMS if t not in used_p1])
                opts_p2 = sorted([t for t in TOP_TEAMS if t not in used_p2])

                idx_t1 = opts_p1.index(current_t1) if current_t1 in opts_p1 else 0
                idx_t2 = opts_p2.index(current_t2) if current_t2 in opts_p2 else 0

                # Colors
                if match['score1'] is None:
                    color_p1, color_p2 = "gray", "gray"
                else:
                    s1, s2 = match['score1'], match['score2']
                    if s1 > s2:
                        color_p1, color_p2 = "#4CAF50", "#FF5252"
                    elif s2 > s1:
                        color_p1, color_p2 = "#FF5252", "#4CAF50"
                    else:
                        color_p1, color_p2 = "#2196F3", "#2196F3"

                with c_home:
                    st.markdown(
                        f"<div style='text-align: right; padding-top: 10px; color: {color_p1}; font-weight: bold;'>{match['p1']}</div>",
                        unsafe_allow_html=True)
                with c_t1:
                    new_t1 = st.selectbox("T1", opts_p1, index=idx_t1, key=f"t1_{match['match_id']}",
                                          label_visibility="collapsed")
                with c_s1:
                    new_s1 = st.number_input("H", value=val_s1, min_value=0, step=1, key=f"s1_{match['match_id']}",
                                             label_visibility="collapsed")
                with c_sep:
                    st.markdown("<div style='text-align: center; padding-top: 10px;'>-</div>", unsafe_allow_html=True)
                with c_s2:
                    new_s2 = st.number_input("A", value=val_s2, min_value=0, step=1, key=f"s2_{match['match_id']}",
                                             label_visibility="collapsed")
                with c_t2:
                    new_t2 = st.selectbox("T2", opts_p2, index=idx_t2, key=f"t2_{match['match_id']}",
                                          label_visibility="collapsed")
                with c_away:
                    st.markdown(
                        f"<div style='padding-top: 10px; color: {color_p2}; font-weight: bold;'>{match['p2']}</div>",
                        unsafe_allow_html=True)
                with c_btn:
                    if st.button("💾", key=f"btn_{match['match_id']}"):
                        # Update Local Data Object
                        idx = data["matches"].index(match)
                        data["matches"][idx]["score1"] = new_s1
                        data["matches"][idx]["score2"] = new_s2
                        data["matches"][idx]["team1"] = new_t1
                        data["matches"][idx]["team2"] = new_t2

                        # Push to Cloud
                        save_data(data)
                        st.toast("Saved to Google Sheets!")
                        st.rerun()
            st.divider()

# TAB 3: Team Tracker
with tab3:
    st.subheader("🛡️ Team Usage Tracker")
    usage_data = []
    for p in sorted(data["players"]):
        used = sorted(list(get_used_teams(data, p)))
        usage_data.append({"Player": p, "Used Count": len(used), "Teams Played": ", ".join(used) if used else "—"})
    st.dataframe(pd.DataFrame(usage_data), use_container_width=True, hide_index=True)