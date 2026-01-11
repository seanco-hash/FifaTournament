import streamlit as st
import pandas as pd
import os
import json

# --- Configuration ---
DATA_FILE = 'tournament_data.json'

TOP_TEAMS = [
    "Manchester City", "Real Madrid", "Bayern Munich", "Liverpool", "Arsenal",
    "Inter Milan", "Bayer Leverkusen", "Paris Saint-Germain", "FC Barcelona",
    "Atletico Madrid", "Juventus", "Borussia Dortmund", "AC Milan", "RB Leipzig",
    "Atalanta", "Benfica", "Sporting CP", "Napoli", "Tottenham Hotspur",
    "Chelsea", "Manchester United", "Newcastle United", "Aston Villa", "Sevilla",
    "Roma", "Lazio", "PSV Eindhoven", "Feyenoord", "Galatasaray", "Ajax"
]


# --- Helper Functions ---
def load_data():
    """Loads data and ensures all players from matches are in the player list."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return {"players": [], "matches": []}

            if "players" not in data: data["players"] = []
            if "matches" not in data: data["matches"] = []

            # --- AUTO-FIX: Scan matches to find any missing players ---
            found_players = set(data["players"])
            for m in data["matches"]:
                if m['p1'] and m['p1'] not in found_players:
                    found_players.add(m['p1'])
                    data["players"].append(m['p1'])
                if m['p2'] and m['p2'] not in found_players:
                    found_players.add(m['p2'])
                    data["players"].append(m['p2'])

            return data
    else:
        return {"players": [], "matches": []}


def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def get_used_teams(data, player_name):
    """Returns a set of teams already used by a specific player."""
    used = set()
    for m in data["matches"]:
        # check p1
        if m['p1'] == player_name and m.get('team1'):
            used.add(m['team1'])
        # check p2
        if m['p2'] == player_name and m.get('team2'):
            used.add(m['team2'])
    return used


def calculate_leaderboard(data):
    players = data["players"]
    matches = data["matches"]

    stats = {p: {'GP': 0, 'W': 0, 'D': 0, 'L': 0, 'GF': 0, 'GA': 0, 'GD': 0, 'Pts': 0} for p in players}

    for m in matches:
        if m.get('score1') is None or m.get('score2') is None:
            continue

        p1, s1 = m['p1'], m['score1']
        p2, s2 = m['p2'], m['score2']

        if p1 not in stats: stats[p1] = {'GP': 0, 'W': 0, 'D': 0, 'L': 0, 'GF': 0, 'GA': 0, 'GD': 0, 'Pts': 0}
        if p2 not in stats: stats[p2] = {'GP': 0, 'W': 0, 'D': 0, 'L': 0, 'GF': 0, 'GA': 0, 'GD': 0, 'Pts': 0}

        stats[p1]['GP'] += 1;
        stats[p2]['GP'] += 1
        stats[p1]['GF'] += s1;
        stats[p1]['GA'] += s2
        stats[p2]['GF'] += s2;
        stats[p2]['GA'] += s1
        stats[p1]['GD'] += (s1 - s2);
        stats[p2]['GD'] += (s2 - s1)

        if s1 > s2:
            stats[p1]['W'] += 1;
            stats[p1]['Pts'] += 3
            stats[p2]['L'] += 1
        elif s2 > s1:
            stats[p2]['W'] += 1;
            stats[p2]['Pts'] += 3
            stats[p1]['L'] += 1
        else:
            stats[p1]['D'] += 1;
            stats[p1]['Pts'] += 1
            stats[p2]['D'] += 1;
            stats[p2]['Pts'] += 1

    df = pd.DataFrame.from_dict(stats, orient='index')
    if not df.empty:
        df = df.sort_values(by=['Pts', 'GD', 'GF'], ascending=False)
        df = df.reset_index().rename(columns={'index': 'Player'})
        df.index += 1
    return df


# --- App Layout ---
st.set_page_config(page_title="🏆 FIFA Manager", layout="wide")
st.title("🏆 FIFA Tournament Manager")

data = load_data()

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("Reload Data"):
        st.rerun()
    st.caption("Matches and Teams are auto-saved.")

# --- Main Tabs ---
tab1, tab2, tab3 = st.tabs(["🥇 Leaderboard", "⚽ Enter Scores", "🛡️ Team Tracker"])

# TAB 1: Leaderboard
with tab1:
    st.subheader("Live Standings")
    if not data["players"]:
        st.info("No players found.")
    else:
        df = calculate_leaderboard(data)
        st.dataframe(df, use_container_width=True, height=600)

# TAB 2: Enter Scores
with tab2:
    st.subheader("Match Schedule")
    matches = data["matches"]

    if not matches:
        st.warning("No matches found.")
    else:
        unique_weeks = sorted(list(set(m.get('week', 0) for m in matches)))

        for week in unique_weeks:
            week_matches = [m for m in matches if m.get('week') == week]
            is_completed = all(m.get('score1') is not None for m in week_matches)
            title_icon = "✅" if is_completed else "📅"

            with st.expander(f"{title_icon} Week {week}", expanded=True):

                for match in week_matches:
                    # Layout: P1 | Team1 | S1 - S2 | Team2 | P2 | Save
                    c_home, c_t1, c_s1, c_sep, c_s2, c_t2, c_away, c_btn = st.columns([2, 2, 0.8, 0.4, 0.8, 2, 2, 1])

                    # --- Data Prep ---
                    val_s1 = int(match['score1']) if match['score1'] is not None else 0
                    val_s2 = int(match['score2']) if match['score2'] is not None else 0
                    current_t1 = match.get('team1')  # Current saved team
                    current_t2 = match.get('team2')  # Current saved team

                    # --- Available Teams Logic ---
                    # Get all teams used by this player in OTHER matches
                    used_p1 = get_used_teams(data, match['p1'])
                    if current_t1 in used_p1: used_p1.remove(current_t1)  # Don't block the currently selected one

                    used_p2 = get_used_teams(data, match['p2'])
                    if current_t2 in used_p2: used_p2.remove(current_t2)  # Don't block the currently selected one

                    # Filter the master list
                    opts_p1 = sorted([t for t in TOP_TEAMS if t not in used_p1])
                    opts_p2 = sorted([t for t in TOP_TEAMS if t not in used_p2])

                    # Insert current team at start if it's not in the list (custom team support)
                    index_t1 = opts_p1.index(current_t1) if current_t1 in opts_p1 else 0
                    index_t2 = opts_p2.index(current_t2) if current_t2 in opts_p2 else 0

                    # --- Visuals ---
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

                    # --- UI Elements ---
                    with c_home:
                        st.markdown(
                            f"<div style='text-align: right; padding-top: 10px; color: {color_p1}; font-weight: bold;'>{match['p1']}</div>",
                            unsafe_allow_html=True)

                    with c_t1:
                        new_t1 = st.selectbox("T1", opts_p1, index=index_t1, key=f"t1_{match['match_id']}",
                                              label_visibility="collapsed")

                    with c_s1:
                        new_s1 = st.number_input("H", value=val_s1, min_value=0, step=1, key=f"s1_{match['match_id']}",
                                                 label_visibility="collapsed")

                    with c_sep:
                        st.markdown("<div style='text-align: center; padding-top: 10px;'>-</div>",
                                    unsafe_allow_html=True)

                    with c_s2:
                        new_s2 = st.number_input("A", value=val_s2, min_value=0, step=1, key=f"s2_{match['match_id']}",
                                                 label_visibility="collapsed")

                    with c_t2:
                        new_t2 = st.selectbox("T2", opts_p2, index=index_t2, key=f"t2_{match['match_id']}",
                                              label_visibility="collapsed")

                    with c_away:
                        st.markdown(
                            f"<div style='padding-top: 10px; color: {color_p2}; font-weight: bold;'>{match['p2']}</div>",
                            unsafe_allow_html=True)

                    with c_btn:
                        if st.button("💾", key=f"btn_{match['match_id']}"):
                            idx = data["matches"].index(match)
                            data["matches"][idx]["score1"] = new_s1
                            data["matches"][idx]["score2"] = new_s2
                            data["matches"][idx]["team1"] = new_t1
                            data["matches"][idx]["team2"] = new_t2
                            save_data(data)
                            st.toast(f"Saved Match {match['match_id']}!")
                            st.rerun()
                st.divider()

# TAB 3: Team Tracker
with tab3:
    st.subheader("🛡️ Team Usage Tracker")
    st.write("Each team can only be used once per player.")

    players = sorted(data["players"])

    # Create a nice summary table
    usage_data = []
    for p in players:
        used = sorted(list(get_used_teams(data, p)))
        count = len(used)
        # Format the list nicely as a string
        teams_str = ", ".join(used) if used else "—"
        usage_data.append({"Player": p, "Used Count": count, "Teams Played": teams_str})

    df_teams = pd.DataFrame(usage_data)
    st.dataframe(df_teams, use_container_width=True, hide_index=True)