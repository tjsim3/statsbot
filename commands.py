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
    save_data()
    await ctx.send(f"Team {team_name} created successfully!")

# ------------- Add Player Command ------------- #
@commands.command()
async def addplayer(ctx, user: discord.Member, level: str = None, team: str = None):
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
    save_data()

    player_obj = Player(user.name)
    print(player_obj)

    await ctx.send(f"{user.display_name} added to {team_name} as {level_name}!")

# ------------- Team Stats Command --------------- #
@commands.command()
async def teamstats(ctx, team: str):
    if team not in team_stats:
        await ctx.send(f"Team {team_name} does not exist!")
        return
    embed = discord.Embed
        title=f"Displaying Team {team}"
        color = 0x00ffff  #cyan
    members = team_stats[team]
    players_with_wr = []
    for player, record in members.items():
        wins = record.get("wins", 0)
        losses = record.get("losses", 0)
        total_games = wins + losses

        if total_games > 0:
            win_rate = (wins / total_games) * 100
        else:
            win_rate = 0.0

        players_with_rates.append((player, win_rate))
        players_with_rates.sort(key=lambda x: x[1], reverse=True)
    
    for player, win_rate in players_with_rates:
        embed.add_field(
            name=player,
            value=f"🏆 {win_rate:.1f}%",
            inline=False
        )
    
        embed.add_field(
            name=player["username"], 
            value=f"Win Rate: {win_rate:.1f}%",
            inline=False
        )
    
    await ctx.send(embed=embed)
    

# ------------- Player Stats Command ------------- #
@commands.command()
async def playerstats(ctx, user: discord.Member):
    player_id = str(user.id)
    if player_id not in player_stats:
        await ctx.send(f"No stats found for {user.display_name}.")
        return

    p = player_stats[player_id]
    wins = p["wins"]
    losses = p["losses"]
    level_index = training_levels.get(player_id, 0)
    level_name = TRAINING_ROLES[level_index]
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

        embed = discord.Embed(
            title = f"📊 Stats for {user.display_name}",
            color = 0x3498db  #blue
        )
        embed.add_field(name="Team", value = p["team"], inline=True)
        embed.add_field(name="Level", value = level_name, inline=True)
        embed.add_field(name="Record", value = f"{wins}-{losses}", inline=True)
        embed.add_field(name="Win Rate", value = f"{win_rate:.1f}%", inline=True)
        await ctx.send(embed=embed)



# -------------- Setup Commands -------------------- #
async def setup(bot):
    bot.add_command(ping) 
    bot.add_command(addteam)
    bot.add_command(addplayer)
    bot.add_command(teamstats)
    bot.add_command(playerstats)
