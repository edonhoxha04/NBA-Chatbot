import streamlit as st
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playercareerstats, leagueleaders, commonplayerinfo
import pandas as pd
import difflib
import re

# --- Page Setup ---
st.set_page_config(page_title="NBA Chatbot", page_icon="🏀")
st.title("🏀 NBA Chatbot")
st.write("Ask me about NBA players, stats, comparisons, top scorers, or general player info.")

# --- Clear Chat Button ---
if st.button("🧹 Clear Chat"):
    st.session_state.chat = []
    st.session_state.last_season = None
    st.session_state.last_player = None
    st.rerun()

# --- Load Player Data ---
all_players = players.get_players()
player_names = [p['full_name'] for p in all_players]

# --- Session State Setup ---
if "chat" not in st.session_state:
    st.session_state.chat = []

if "last_player" not in st.session_state:
    st.session_state.last_player = None

if "last_season" not in st.session_state:
    st.session_state.last_season = None

# --- Helper Functions ---
def extract_season_year(text):
    match = re.search(r'\b(20[0-9]{2}|19[0-9]{2})\b', text)
    return match.group(1) if match else None

def find_player_id(player_name):
    for player in all_players:
        if player['full_name'].lower() == player_name.lower():
            return player['id']
    return None

def get_stats_for_season(player_id, season_year=None):
    career = playercareerstats.PlayerCareerStats(player_id=player_id)
    df = career.get_data_frames()[0]

    if season_year:
        season_id = f"{int(season_year)-1}-{str(season_year)[-2:]}"
        season_row = df[df["SEASON_ID"] == season_id]
        if season_row.empty:
            return None  # No fallback
        row = season_row.iloc[0]
    else:
        row = df.iloc[-1]

    return {
        "season": row["SEASON_ID"],
        "team": row["TEAM_ABBREVIATION"],
        "pts": row["PTS"],
        "ast": row["AST"],
        "reb": row["REB"],
        "games": row["GP"],
        "fg_pct": row["FG_PCT"]
    }

def find_closest_names(text, limit=2):
    return difflib.get_close_matches(text, player_names, n=limit, cutoff=0.5)

def find_multiple_players(text):
    found = []
    for name in player_names:
        if name.lower() in text.lower():
            found.append(name)
        if len(found) == 2:
            break
    return found if len(found) == 2 else None

def compare_players(name1, name2, season_year=None):
    id1 = find_player_id(name1)
    id2 = find_player_id(name2)

    if not id1 or not id2:
        return f"Could not find both players: {name1} and {name2}."

    stats1 = get_stats_for_season(id1, season_year)
    stats2 = get_stats_for_season(id2, season_year)

    if stats1 is None or stats2 is None:
        return f"❌ Stats not available for one or both players in {season_year}."

    return (
        f"📊 **{name1} vs {name2}** in {stats1['season']}:\n\n"
        f"| Stat     | {name1} | {name2} |\n"
        f"|----------|---------|---------|\n"
        f"| Team     | {stats1['team']} | {stats2['team']} |\n"
        f"| Games    | {stats1['games']} | {stats2['games']} |\n"
        f"| PPG      | {stats1['pts']:.1f} | {stats2['pts']:.1f} |\n"
        f"| APG      | {stats1['ast']:.1f} | {stats2['ast']:.1f} |\n"
        f"| RPG      | {stats1['reb']:.1f} | {stats2['reb']:.1f} |\n"
        f"| FG%      | {stats1['fg_pct']*100:.1f}% | {stats2['fg_pct']*100:.1f}% |\n"
    )

def get_top_scorers(season_year, stat='PTS'):
    season_id = f"{int(season_year)-1}-{str(season_year)[-2:]}"
    try:
        leaders = leagueleaders.LeagueLeaders(season=season_id)
        df = leaders.get_data_frames()[0]
        top5 = df[['PLAYER', 'TEAM', stat]].head(5)
        response = f"🏀 Top 5 players by {stat} in {season_id}:\n\n"
        response += "| Rank | Player | Team | " + stat + " |\n|------|--------|------|------|\n"
        for i, row in top5.iterrows():
            response += f"| {i+1} | {row['PLAYER']} | {row['TEAM']} | {row[stat]:.1f} |\n"
        return response
    except:
        return f"Couldn't fetch top {stat} leaders for {season_id}."

def get_career_averages(player_id):
    career = playercareerstats.PlayerCareerStats(player_id=player_id)
    df = career.get_data_frames()[0]
    row = df.iloc[-1]
    return {
        "pts": row["PTS"],
        "ast": row["AST"],
        "reb": row["REB"],
        "games": row["GP"],
        "fg_pct": row["FG_PCT"]
    }

def get_player_bio(name):
    player = next((p for p in all_players if p["full_name"].lower() == name.lower()), None)
    if not player:
        return "Player not found."

    player_id = player["id"]
    try:
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        data = info.get_data_frames()[0].iloc[0]

        def safe(field):
            value = data.get(field, "N/A")
            if pd.isna(value) or value == "":
                return "N/A"
            return value

        return (
            f"🧬 **{safe('DISPLAY_FIRST_LAST')}**\n\n"
            f"**Position:** {safe('POSITION')}\n\n"
            f"**Team:** {safe('TEAM_NAME')} ({safe('TEAM_ABBREVIATION')})\n\n"
            f"**Height:** {safe('HEIGHT')}  |  **Weight:** {safe('WEIGHT')} lbs\n\n"
            f"**Birth Date:** {safe('BIRTHDATE')[:10] if safe('BIRTHDATE') != 'N/A' else 'N/A'}\n\n"
            f"**Country:** {safe('COUNTRY')}\n\n"
            f"**Draft Info:** {safe('DRAFT_YEAR')} Round {safe('DRAFT_ROUND')}, Pick {safe('DRAFT_NUMBER')}\n\n"
            f"**Years Pro:** {safe('SEASON_EXP')}\n\n"
            f"**Is Active:** {'✅ Yes' if player['is_active'] else '❌ No'}"
        )
    except Exception as e:
        return f"❌ Could not fetch detailed bio for {name}. Error: {str(e)}"

# --- Generate Response ---
def generate_response(user_input):
    text = user_input.lower()
    season_year = extract_season_year(text)
    players_in_text = find_multiple_players(text)

    if not season_year:
        season_year = st.session_state.last_season
    else:
        st.session_state.last_season = season_year

    player_name = find_closest_names(user_input, limit=1)
    if player_name:
        player_name = player_name[0]
        st.session_state.last_player = player_name
    else:
        player_name = st.session_state.last_player

    # --- Top Scorers ---
    if "top" in text and ("scorers" in text or "points" in text or "ppg" in text):
        if season_year:
            return get_top_scorers(season_year, stat='PTS')
        else:
            return "Please specify a year, like 'Top scorers 2022'."

    # --- Career Stats ---
    if player_name and ("career" in text or "all-time" in text or "all time" in text):
        pid = find_player_id(player_name)
        if not pid:
            return f"Player {player_name} not found."
        career = get_career_averages(pid)
        return (
            f"📈 Career Averages for {player_name}:\n"
            f"- Games: {career['games']}\n"
            f"- PPG: {career['pts']:.1f}\n"
            f"- APG: {career['ast']:.1f}\n"
            f"- RPG: {career['reb']:.1f}\n"
            f"- FG%: {career['fg_pct']*100:.1f}%"
        )

    # --- Player Bio ---
    if player_name and ("bio" in text or "info" in text):
        return get_player_bio(player_name)

    # --- Comparison ---
    if players_in_text:
        return compare_players(players_in_text[0], players_in_text[1], season_year)

    # --- One Player Stat Query ---
    if not player_name:
        return "I couldn't recognize any player. Try again with a name like 'LeBron James'."

    stats = get_stats_for_season(find_player_id(player_name), season_year)
    if stats is None:
        if season_year:
            return f"❌ {player_name} did not play in the {int(season_year)-1}-{str(season_year)[-2:]} season."
        else:
            return f"❌ No stats found for {player_name}."

    if "points" in text or "ppg" in text:
        return f"{player_name} scored {stats['pts']:.1f} PPG in the {stats['season']} season."
    elif "assists" in text or "apg" in text:
        return f"{player_name} made {stats['ast']:.1f} APG in the {stats['season']} season."
    elif "rebounds" in text or "rpg" in text:
        return f"{player_name} got {stats['reb']:.1f} RPG in the {stats['season']} season."
    elif "team" in text:
        return f"{player_name} played for {stats['team']} in the {stats['season']} season."
    elif "fg" in text or "field goal" in text:
        return f"{player_name}'s FG% in the {stats['season']} season was {stats['fg_pct']*100:.1f}%."
    else:
        return (f"{player_name} in the {stats['season']} season (with {stats['team']}):\n"
                f"Games: {stats['games']}, PPG: {stats['pts']:.1f}, "
                f"APG: {stats['ast']:.1f}, RPG: {stats['reb']:.1f}, FG%: {stats['fg_pct']*100:.1f}%")

# --- User Input ---
user_input = st.text_input("You:", placeholder="Try: 'Compare LeBron and Curry 2021' or 'Top scorers 2023'")

if user_input:
    st.session_state.chat.append(("You", user_input))
    response = generate_response(user_input)
    st.session_state.chat.append(("Bot", response))

# --- Chat Display ---
for speaker, msg in st.session_state.chat:
    if speaker == "You":
        st.markdown(f"**🧍 You:** {msg}")
    else:
        st.markdown(f"**🤖 Bot:** {msg}")
