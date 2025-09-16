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
    return {"players": {}, "TEAMS": {}, "timezones": {}}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({
            "players": player_stats,
            "TEAMS": team_stats,
            "timezones": timezones
        }, f, indent=4)

# Load data into memory
_data = load_data()
player_stats = _data.get("players", {})       # {player_id: {wins, losses, team, training_level}}
team_stats = _data.get("TEAMS", {})           # {team_name: {wins, losses, games_played}}
timezones = _data.get("timezones", {})        # {player_id: timezone_role}

#---------------------------Variables-----------------------------------#
# Roles for training levels (rank progression)
TRAINING_ROLES = ["Apprentice", "Wizard", "Sage"]
#teams dict
TEAMS = {}
class Player:
    def __init__(self, username: str):
        self.username = username
        self.wins = 0
        self.losses = 0
        self.level = 0

    @property
    def training_role(self):
        return TRAINING_ROLES[self.level]
        
    def win_percent(self):
        total_games = self.wins + self.losses
        if total_games == 0:
            return 0.0
        return (self.wins / total_games) * 100 if total_games > 0 else 0

    def record_win(self):
        self.wins += 1

    def record_loss(self):
        self.losses += 1

    def __repr__(self):
        return f"<Player {self.username}: {self.wins}-{self.losses}, {self.win_percent:.1f}% WR>"



#---------------------------BOT COMMANDS--------------------------------#

#creation commands------------------------------------------------------#
@commands.command()
async def addteam(ctx, team_name: str, roleID: str):
    if team_name not in TEAMS:
        role = discord.utils.get(ctx.guild.roles, name=roleID)
        TEAMS[team_name] = {
            "members": [],
            "wins": 0,
            "losses": 0,
            "role": role
        }
        await ctx.send(f"Team {team_name} created successfully!")
    else:
        await ctx.send(f"Team {team_name} already exists!")


@commands.command()
async def addplayer(ctx, user: discord.Member, level: str = None, team: str = None):
    player = user 
    for team_name, data in TEAMS.items():
        if player.id in data["members"]:
            await ctx.send(f"{player.display_name} is already in {team_name}!")
            return
    if team is None:
        team_name = list(TEAMS.keys())[0]
    else:
        team_name = team
    
    await player.add_roles(TEAMS[team_name]["role"])
    if level is None:
        level = TRAINING_ROLES[0]
        role = discord.utils.get(ctx.guild.roles, name=level)
        await player.add_roles(role)
    
    player1 = Player(player.name)
    print(player1.username)
    print(player1.wins)
    print(player1.losses)
    print(player1.level)
    print(player1.training_role)
    spellkeeperrole = discord.utils.get(ctx.guild.roles, name="Spellkeeper")
    player.add_roles(spellkeeperrole)
    TEAMS[team_name]["members"].append(player1)
    player_stats[str(player.id)] = {
        "username": player.name,
        "wins": 0,
        "losses": 0,
        "level": 0,
        "team": team_name
    }
    save_data()
    return
