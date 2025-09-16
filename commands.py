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
TEAMS = {}
class Player:
    def __init__(self, username: str):
        self.username = username
        self.wins = 0
        self.losses = 0
        self.level = 0

    @property
    def training_role(self):
        return self.TRAINING_ROLES[self.level]
        
    def win_percent(self):
        total_games = self.wins + self.losses
        if total_games == 0:
            return 0.0
        return (self.wins / total_games) * 100

    def record_win(self):
        self.wins += 1

    def record_loss(self):
        self.losses += 1

    def __repr__(self):
        return f"<Player {self.username}: {self.wins}-{self.losses}, {self.win_percent:.1f}% WR>"


#---------------------------BOT COMMANDS--------------------------------#

#creation commands
@commands.command
async def addteam(team_name: str, roleID: str):
    if team_name not in TEAMS:
        TEAMS[team_name] = {
            "members": [],
            "wins": 0,
            "losses": 0
            "role" = discord.utils.get(ctx.guild.roles, name=roleID)
        }
        await ctx.send(f"Team {team_name} created successfully!"}
    else:
        await ctx.send(f"Team {team_name} already exists!")

@commands.command
async def addplayer(user, level: str = none, team: str = none):
    player = ctx.guild.get_member(user)
    if player = none
        await ctx.send("Player not found in server!")
    for team_name in TEAMS
        for member in TEAMS[team_name]["members"]
            if user == member
                await ctx.send(f"{member} is already in {team_name}! You may edit this player using <edit player")
                break
                
    if team is none:
        team = TEAMS[0]
        await player.add_roles(TEAMS[0]["role"])
        print("default team added for {user}")
    else 
        await player.add_roles(TEAMS[team]["role"])
                
    if level is none:
        level = TRAINING_ROLES[0]
        await player.add_roles(TRAINING_ROLES[0])
        print("default training level added for {user}")
    else 
        await player.add_roles(TRAINING_ROLES[level]) 

    player1 = Player(user)
    print(player1.username)       
    print(player1.wins)           
    print(player1.losses)         
    print(player1.level)          
    print(player1.training_role)  
                    
