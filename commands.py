import discord
from discord.ext import commands
from discord.ext.commands import has_role
import json
import os
import time
import asyncio


# ---------------- Persistence Helpers ---------------- #
DATA_FILE = "stats.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"players": {}, "TEAMS": {}, "training_levels": {}}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({
            "players": player_stats,
            "TEAMS": team_stats,
            "training_levels": training_levels
        }, f, indent=4)

_data = load_data()
player_stats = _data.get("players", {})       
team_stats = _data.get("TEAMS", {})           
training_levels = _data.get("training_levels", {})

#--------------Other Helpers--------------#
def find_player_by_name(name: str):
    matches = []
    for player_id, record in player_stats.items():
        username = record["username"].lower()
        if name.lower() in username:
            matches.append((player_id, record))
    return matches

#---------------------------Variables-----------------------------------#
TRAINING_ROLES = ["Apprentice", "Wizard", "Sage"]

#---------------------------Player Class--------------------------------#
class Player:
    def __init__(self, username: str, wins: int = 0, losses: int = 0, level: int = 0):
        self.username = username
        self.wins = wins
        self.losses = losses
        self.level = level

    @property
    def training_role(self):
        return TRAINING_ROLES[self.level]

    def win_percent(self):
        total = self.wins + self.losses
        return (self.wins / total) * 100 if total > 0 else 0

    def record_win(self):
        self.wins += 1

    def record_loss(self):
        self.losses += 1

    def __repr__(self):
        return f"<Player {self.username}: {self.wins}-{self.losses}, {self.win_percent():.1f}% WR>"

#---------------------------BOT COMMANDS--------------------------------#
@commands.command()
async def ping(ctx):
    await ctx.send("Pong")

# ------------- Add Team Command ------------- #
@commands.command()
async def addteam(ctx, team_name: str, role_name: str):
    """Create a new team with a specified Discord role"""
    if team_name in team_stats:
        await ctx.send(f"Team {team_name} already exists!")
        return

    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role is None:
        await ctx.send(f"Role {role_name} not found in the server!")
        return

    team_stats[team_name] = {
        "members": [],      # store player IDs as strings
        "wins": 0,
        "losses": 0,
        "role": role_name   # store role name as string
    }
    await ctx.send(f"Team {team_name} created successfully!")
    save_data()

# ------------ Delete Team Command ------------- #
@commands.command()
async def deleteteam(ctx, team_name: str):
    """Delete a team and remove all players from it"""
    if team_name not in team_stats:
        await ctx.send(f"Team {team_name} does not exist!")
        return

    # Remove team from all players
    for player_id in team_stats[team_name]["members"]:
        if player_id in player_stats:
            player_stats[player_id]["team"] = None

    del team_stats[team_name]
    await ctx.send(f"🗑️ Team {team_name} deleted successfully!")
    save_data()

# ------------- Add Player Command ------------- #
@commands.command()
async def addplayer(ctx, username: str, level: str = None, team: str = None):
    """Add a new player to a team with a training level"""
    matches = [m for m in ctx.guild.members if username.lower() in m.name.lower()]
    if not matches:
        await ctx.send(f"No user found matching '{username}'.")
        return
    if len(matches) > 1:
        names = ", ".join(m.name for m in matches)
        await ctx.send(f"Multiple users found: {names}. Please be more specific.")
        return

    user = matches[0]
    player_id = str(user.id)

    for t_name, data in team_stats.items():
        if player_id in data["members"]:
            await ctx.send(f"{user.display_name} is already in {t_name}!")
            return

    if not team_stats:
        await ctx.send("No teams exist! Please create a team first using <addteam>")
        return

    team_name = team if team else list(team_stats.keys())[0]
    if team_name not in team_stats:
        await ctx.send(f"Team {team_name} does not exist!")
        return

    team_stats[team_name]["members"].append(player_id)

    team_role_name = team_stats[team_name]["role"]
    team_role = discord.utils.get(ctx.guild.roles, name=team_role_name)
    if team_role:
        await user.add_roles(team_role)

    level_name = level if level else TRAINING_ROLES[0]
    level_index = TRAINING_ROLES.index(level_name)
    training_levels[player_id] = level_index

    level_role = discord.utils.get(ctx.guild.roles, name=level_name)
    if level_role:
        await user.add_roles(level_role)

    spellkeeper_role = discord.utils.get(ctx.guild.roles, name="Spellkeeper")
    if spellkeeper_role:
        await user.add_roles(spellkeeper_role)

    player_stats[player_id] = {
        "username": user.name,
        "wins": 0,
        "losses": 0,
        "team": team_name
    }

    await ctx.send(f"{user.display_name} added to {team_name} as {level_name}!")
    save_data()

# ------------- Edit Player Command -------------- #
@commands.command()
async def editplayer(ctx, username: str, wins: int = None, losses: int = None, team: str = None):
    """Edit a player's stats or team"""
    matches = find_player_by_name(username)
    if not matches:
        await ctx.send(f"No player found matching '{username}'.")
        return
    if len(matches) > 1:
        names = ", ".join(r["username"] for _, r in matches)
        await ctx.send(f"Multiple players found: {names}. Please be more specific.")
        return

    player_id, record = matches[0]
    if wins is not None:
        record["wins"] = wins
    if losses is not None:
        record["losses"] = losses
    if team is not None:
        if team not in team_stats:
            await ctx.send(f"Team {team} does not exist!")
            return
        # Remove from old team
        old_team = record["team"]
        if player_id in team_stats.get(old_team, {}).get("members", []):
            team_stats[old_team]["members"].remove(player_id)
        # Add to new team
        team_stats[team]["members"].append(player_id)
        record["team"] = team

    await ctx.send(f"✅ {record['username']} updated successfully!")
    save_data()


# ------------- Delete Player Command ------------ #
@commands.command()
async def deleteplayer(ctx, username: str):
    """Delete a player from the system"""
    matches = find_player_by_name(username)
    if not matches:
        await ctx.send(f"No player found matching '{username}'.")
        return
    if len(matches) > 1:
        names = ", ".join(r["username"] for _, r in matches)
        await ctx.send(f"Multiple players found: {names}. Please be more specific.")
        return

    player_id, record = matches[0]
    team_name = record["team"]
    if player_id in team_stats.get(team_name, {}).get("members", []):
        team_stats[team_name]["members"].remove(player_id)
    player_stats.pop(player_id, None)
    training_levels.pop(player_id, None)

    await ctx.send(f"🗑️ Player {record['username']} deleted successfully!")
    save_data()


# ------------- Team Stats Command --------------- #
@commands.command()
async def teamstats(ctx, team: str):
    """Show stats for a specific team"""
    if team not in team_stats:
        await ctx.send(f"Team {team} does not exist!")
        return

    embed = discord.Embed(
        title=f"Displaying Team {team}",
        color=0x00ffff  # cyan
    )

    members = team_stats[team]["members"]  # list of player IDs
    players_with_rates = []

    for player_id in members:
        record = player_stats.get(player_id, {"wins": 0, "losses": 0, "username": "Unknown"})
        wins = record.get("wins", 0)
        losses = record.get("losses", 0)
        total_games = wins + losses
        win_rate = (wins / total_games) * 100 if total_games > 0 else 0.0

        players_with_rates.append((record["username"], win_rate))

    # Sort by winrate descending
    players_with_rates.sort(key=lambda x: x[1], reverse=True)

    for username, win_rate in players_with_rates:
        embed.add_field(
            name=username,
            value=f"🏆 {win_rate:.1f}%",
            inline=False
        )

    await ctx.send(embed=embed)
    save_data()


# ------------- Player Stats Command ------------- #
@commands.command()
async def playerstats(ctx, username: str):
    """Show stats for a specific player"""
    matches = find_player_by_name(username)
    if not matches:
        await ctx.send(f"No player found matching '{username}'.")
        return
    if len(matches) > 1:
        names = ", ".join(r["username"] for _, r in matches)
        await ctx.send(f"Multiple players found: {names}. Please be more specific.")
        return

    player_id, record = matches[0]
    wins = record["wins"]
    losses = record["losses"]
    level_index = training_levels.get(player_id, 0)
    level_name = TRAINING_ROLES[level_index]
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

    embed = discord.Embed(
        title=f"📊 Stats for {record['username']}",
        color=0x3498db  # blue
    )
    embed.add_field(name="Team", value=record["team"], inline=True)
    embed.add_field(name="Level", value=level_name, inline=True)
    embed.add_field(name="Record", value=f"{wins}-{losses}", inline=True)
    embed.add_field(name="Win Rate", value=f"{win_rate:.1f}%", inline=True)

    await ctx.send(embed=embed)

# ------------- Players Command --------------------- #
@commands.command(name="players")
async def players(ctx):
    """List all players sorted by winrate"""
    if not player_stats:
        await ctx.send("No players found!")
        return

    embed = discord.Embed(
        title="🏅 Player Rankings by Winrate",
        color=0xffd700  # gold
    )

    players_with_rates = []
    for player_id, record in player_stats.items():
        wins = record.get("wins", 0)
        losses = record.get("losses", 0)
        total_games = wins + losses
        win_rate = (wins / total_games) * 100 if total_games > 0 else 0.0
        players_with_rates.append((record["username"], win_rate, wins, losses))
    players_with_rates.sort(key=lambda x: x[1], reverse=True)
    for username, win_rate, wins, losses in players_with_rates:
        embed.add_field(
            name=username,
            value=f"Record: {wins}-{losses} | 🏆 {win_rate:.1f}%",
            inline=False
        )

    await ctx.send(embed=embed)
    save_data()


# ------------- Teams Command --------------------- #
@commands.command(name="teams")
async def teams(ctx):
    """List all teams with their records and member counts"""
    if not team_stats:
        await ctx.send("No teams have been created yet!")
        return

    embed = discord.Embed(
        title="📋 Teams (Most Recent First)",
        color=0x1abc9c  # teal
    )
    team_list = list(team_stats.items())[::-1]

    for team_name, data in team_list:
        wins = data.get("wins", 0)
        losses = data.get("losses", 0)
        embed.add_field(
            name=team_name,
            value=f"Record: {wins}-{losses}, Members: {len(data['members'])}",
            inline=False
        )

    await ctx.send(embed=embed)
    save_data()

# -------------- Rosters Command -------------------- #
# -------------- Rosters Command -------------------- #
@commands.command(name="rosters")
async def rosters(ctx, team_name: str):
    """Generate balanced rosters for 2v2 and 3v3 games"""
    
    if team_name not in team_stats:
        await ctx.send(f"❌ Team {team_name} does not exist!")
        return
    
    team_data = team_stats[team_name]
    member_ids = team_data["members"]
    
    if not member_ids:
        await ctx.send(f"❌ Team {team_name} has no players!")
        return
    
    await ctx.send(f"🎮 **Starting roster creation for {team_name}**\n"
                   f"Season has **12 total games**: 8 x 2v2 and 4 x 3v3\n"
                   f"We need to fill one side of each game.\n\n"
                   f"Please respond with each player's info when prompted.\n")
    
    # Step 1: Collect player availability
    player_availability = {}
    
    for player_id in member_ids:
        record = player_stats.get(player_id)
        if not record:
            continue
            
        username = record["username"]
        
        # Ask for max games
        await ctx.send(f"📝 **{username}**: How many games maximum? (0-12)")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
        
        try:
            msg = await ctx.bot.wait_for('message', timeout=60.0, check=check)
            max_games = int(msg.content)
            
            if max_games < 0 or max_games > 12:
                await ctx.send(f"⚠️ Invalid number. Setting {username} to 0 games.")
                max_games = 0
            
            player_availability[player_id] = {
                "username": username,
                "max_games": max_games,
                "wins": record.get("wins", 0),
                "losses": record.get("losses", 0),
                "games_assigned": 0,
                "away": False
            }
            
        except asyncio.TimeoutError:
            await ctx.send(f"⏰ No response for {username}. Skipping them.")
            continue
    
    # Step 2: Ask about away games
    await ctx.send(f"\n🚀 **Away Games**: Are there any players from OTHER teams playing games for {team_name}?\n"
                   f"Type player names separated by commas, or type 'none' if no away players.")
    
    try:
        def msg_check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        msg = await ctx.bot.wait_for('message', timeout=60.0, check=msg_check)
        away_input = msg.content.strip().lower()
        
        if away_input != 'none':
            away_names = [name.strip() for name in away_input.split(',')]
            
            for name in away_names:
                matches = find_player_by_name(name)
                if matches and len(matches) == 1:
                    player_id, record = matches[0]
                    
                    await ctx.send(f"📝 **{record['username']}** (Away Player): How many games for {team_name}? (0-12)")
                    
                    try:
                        msg = await ctx.bot.wait_for('message', timeout=30.0, 
                                                      check=lambda m: m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit())
                        max_games = int(msg.content)
                        
                        if max_games < 0 or max_games > 12:
                            max_games = 0
                        
                        player_availability[player_id] = {
                            "username": record["username"],
                            "max_games": max_games,
                            "wins": record.get("wins", 0),
                            "losses": record.get("losses", 0),
                            "games_assigned": 0,
                            "away": True
                        }
                        
                    except asyncio.TimeoutError:
                        await ctx.send(f"⏰ Skipping {record['username']}")
                else:
                    await ctx.send(f"⚠️ Could not find unique player matching '{name}'")
                        
    except asyncio.TimeoutError:
        await ctx.send("⏰ No away games added.")
    
    # Step 3: Rank players by skill (win rate %)
    available_players = []
    for player_id, data in player_availability.items():
        if data["max_games"] > 0:
            total_games = data["wins"] + data["losses"]
            win_rate = (data["wins"] / total_games * 100) if total_games > 0 else 0
            available_players.append({
                "id": player_id,
                "username": data["username"],
                "win_rate": win_rate,
                "max_games": data["max_games"],
                "games_assigned": 0,
                "away": data["away"]
            })
    
    # Sort by win rate descending (best players first)
    available_players.sort(key=lambda x: x["win_rate"], reverse=True)
    
    if len(available_players) < 2:
        await ctx.send(f"❌ Not enough players available! Need at least 2 players.")
        return
    
    await ctx.send("⚙️ Generating balanced rosters...")
    
    # Step 4: Helper function to get next available player
    def get_available_player(exclude_ids=None):
        """Get next player with games remaining, excluding specific IDs"""
        if exclude_ids is None:
            exclude_ids = set()
        
        for player in available_players:
            if player["id"] not in exclude_ids and player["games_assigned"] < player["max_games"]:
                return player
        return None
    
    # Step 5: Generate 3v3 rosters FIRST (4 games, higher priority)
    rosters_3v3 = []
    
    for game_num in range(4):
        team = []
        used_ids = set()
        
        # Try to balance: 1 strong + 1 medium + 1 weak
        # Pick from top third (strong)
        strong_player = None
        for player in available_players[:len(available_players)//3 + 1]:
            if player["id"] not in used_ids and player["games_assigned"] < player["max_games"]:
                strong_player = player
                break
        
        if strong_player:
            team.append((strong_player["id"], strong_player["username"]))
            strong_player["games_assigned"] += 1
            used_ids.add(strong_player["id"])
        
        # Pick from middle third (medium)
        medium_player = None
        mid_start = len(available_players) // 3
        mid_end = 2 * len(available_players) // 3
        for player in available_players[mid_start:mid_end + 1]:
            if player["id"] not in used_ids and player["games_assigned"] < player["max_games"]:
                medium_player = player
                break
        
        if medium_player:
            team.append((medium_player["id"], medium_player["username"]))
            medium_player["games_assigned"] += 1
            used_ids.add(medium_player["id"])
        
        # Pick from bottom third (weak)
        weak_player = None
        for player in reversed(available_players):
            if player["id"] not in used_ids and player["games_assigned"] < player["max_games"]:
                weak_player = player
                break
        
        if weak_player:
            team.append((weak_player["id"], weak_player["username"]))
            weak_player["games_assigned"] += 1
            used_ids.add(weak_player["id"])
        
        # If we couldn't get balanced team, fill with anyone available
        while len(team) < 3:
            next_player = get_available_player(used_ids)
            if next_player:
                team.append((next_player["id"], next_player["username"]))
                next_player["games_assigned"] += 1
                used_ids.add(next_player["id"])
            else:
                break
        
        if len(team) == 3:
            rosters_3v3.append(team)
        else:
            break  # Can't fill more 3v3 games
    
    # Step 6: Generate 2v2 rosters (8 games)
    rosters_2v2 = []
    
    for game_num in range(8):
        team = []
        used_ids = set()
        
        # Try to balance: 1 strong + 1 weak
        # Pick strong player from top half
        strong_player = None
        for player in available_players[:len(available_players)//2 + 1]:
            if player["id"] not in used_ids and player["games_assigned"] < player["max_games"]:
                strong_player = player
                break
        
        if strong_player:
            team.append((strong_player["id"], strong_player["username"]))
            strong_player["games_assigned"] += 1
            used_ids.add(strong_player["id"])
        
        # Pick weak player from bottom half
        weak_player = None
        for player in reversed(available_players):
            if player["id"] not in used_ids and player["games_assigned"] < player["max_games"]:
                weak_player = player
                break
        
        if weak_player:
            team.append((weak_player["id"], weak_player["username"]))
            weak_player["games_assigned"] += 1
            used_ids.add(weak_player["id"])
        
        # If we couldn't get balanced team, fill with anyone available
        while len(team) < 2:
            next_player = get_available_player(used_ids)
            if next_player:
                team.append((next_player["id"], next_player["username"]))
                next_player["games_assigned"] += 1
                used_ids.add(next_player["id"])
            else:
                break
        
        if len(team) == 2:
            rosters_2v2.append(team)
        else:
            break  # Can't fill more 2v2 games
    
    # Step 7: Display results
    embed = discord.Embed(
        title=f"🎯 Season Rosters for {team_name}",
        description=f"Total: {len(rosters_2v2) + len(rosters_3v3)} out of 12 games filled",
        color=0x00ff00
    )
    
    # 3v3 Section
    if rosters_3v3:
        games_3v3_text = ""
        for i, team in enumerate(rosters_3v3, 1):
            players = " + ".join([username for _, username in team])
            games_3v3_text += f"**Game {i}:** {players}\n"
        
        embed.add_field(name="⚔️ 3v3 Games (4 total)", value=games_3v3_text, inline=False)
    else:
        embed.add_field(name="⚔️ 3v3 Games", value="❌ Could not fill any 3v3 games", inline=False)
    
    # 2v2 Section
    if rosters_2v2:
        games_2v2_text = ""
        for i, team in enumerate(rosters_2v2, 1):
            players = " + ".join([username for _, username in team])
            games_2v2_text += f"**Game {i}:** {players}\n"
        
        embed.add_field(name="🎮 2v2 Games (8 total)", value=games_2v2_text, inline=False)
    else:
        embed.add_field(name="🎮 2v2 Games", value="❌ Could not fill any 2v2 games", inline=False)
    
    # Player Usage Summary
    usage_text = ""
    for player in sorted(available_players, key=lambda x: x["games_assigned"], reverse=True):
        away_marker = " (Away)" if player["away"] else ""
        usage_text += f"{player['username']}{away_marker}: {player['games_assigned']}/{player['max_games']} games\n"
    
    if len(usage_text) > 1024:  # Discord field limit
        usage_text = usage_text[:1000] + "...\n(List truncated)"
    
    embed.add_field(name="📊 Player Usage", value=usage_text, inline=False)
    
    # Summary
    total_filled = len(rosters_2v2) + len(rosters_3v3)
    summary = f"✅ {len(rosters_3v3)}/4 3v3 games • {len(rosters_2v2)}/8 2v2 games • {total_filled}/12 total"
    embed.set_footer(text=summary)
    
    await ctx.send(embed=embed)

# ------------- Export Command --------------------- #
@commands.command()
async def exportrosters(ctx, team_name: str):
    """Export team rosters to a text file"""
    if team_name not in team_stats:
        await ctx.send(f"❌ Team {team_name} does not exist!")
        return
    
    members = team_stats[team_name]["members"]
    
    # Create text file content
    content = f"=== {team_name} Roster ===\n\n"
    
    for level in TRAINING_ROLES:
        players_at_level = []
        for player_id in members:
            record = player_stats.get(player_id)
            if record and training_levels.get(player_id, 0) == TRAINING_ROLES.index(level):
                wins = record.get("wins", 0)
                losses = record.get("losses", 0)
                win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
                players_at_level.append(f"  - {record['username']} ({wins}-{losses}, {win_rate:.1f}%)")
        
        if players_at_level:
            content += f"{level}s:\n"
            content += "\n".join(players_at_level)
            content += "\n\n"
    
    # Create file
    filename = f"{team_name}_roster.txt"
    with open(filename, "w") as f:
        f.write(content)
    
    # Send file
    await ctx.send(f"📄 Roster exported!", file=discord.File(filename))
    
    # Clean up
    os.remove(filename)


# -------------- Leaders Help Command -------------------- #
@commands.command(name="leadershelp")
async def leadersHelp(ctx):
    """Show all available commands for team leaders"""
    embed = discord.Embed(
        title="📜 Team Management Commands",
        description="Commands for managing teams and players",
        color=0x9b59b6
    )
    
    embed.add_field(
        name="🏰 Team Commands",
        value=(
            "`%addteam <name> <role>` - Create a new team\n"
            "`%deleteteam <name>` - Delete a team\n"
            "`%teams` - List all teams\n"
            "`%roster <team>` - View team roster by level\n"
            "`%teamstats <team>` - View team stats\n"
            "`%exportrosters <team>` - Export roster to file"
        ),
        inline=False
    )
    
    embed.add_field(
        name="👥 Player Commands",
        value=(
            "`%addplayer <user> [level] [team]` - Add one player\n"
            "`%bulkaddplayers <team> <level> <user1> <user2>...` - Add multiple\n"
            "`%editplayer <user> [wins] [losses] [team]` - Edit player\n"
            "`%deleteplayer <user>` - Remove player\n"
            "`%promote <user>` - Promote to next level\n"
            "`%demote <user>` - Demote to previous level\n"
            "`%players` - List all players\n"
            "`%playerstats <user>` - View player stats"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎮 Game Commands",
        value=(
            "`%rosters <team>` - Generate season rosters\n"
            "`%recordmatch <winner> <loser> <players>` - Record match result"
        ),
        inline=False
    )
    
    embed.set_footer(text="Training Levels: Apprentice → Wizard → Sage")
    
    await ctx.send(embed=embed)

# -------------- Setup Commands -------------------- #
async def setup(bot):
    bot.add_command(ping) 
    bot.add_command(addteam)
    bot.add_command(addplayer)
    bot.add_command(teamstats)
    bot.add_command(playerstats)
    bot.add_command(teams)
    bot.add_command(players)
    bot.add_command(editplayer)
    bot.add_command(deleteplayer)
    bot.add_command(deleteteam)
    bot.add_command(rosters)
    bot.add_command(exportrosters)
    bot.add_command(leadersHelp)