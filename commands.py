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
