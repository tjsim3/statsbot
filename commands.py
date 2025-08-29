import discord
from discord.ext import commands
from discord.ext.commands import has_role
import json
import os

# ---------------- Persistence Helpers ---------------- #
DATA_FILE = "stats.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"players": {}, "teams": {}, "timezones": {}}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({
            "players": player_stats,
            "teams": team_stats,
            "timezones": timezones
        }, f, indent=4)

# Load data into memory
_data = load_data()
player_stats = _data.get("players", {})       # {player_id: {wins, losses, team, training_level}}
team_stats = _data.get("teams", {})           # {team_name: {wins, losses, games_played}}
timezones = _data.get("timezones", {})        # {player_id: timezone_role}

# Roles for training levels (rank progression)
TRAINING_ROLES = ["Apprentice", "Wizard", "Sage"]

class StatsBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- High Mage Commands ---------------- #

    @commands.command(name="winrate")
    @has_role("high mage")
    async def winrate(self, ctx, member: discord.Member = None):
        """Displays winrate of an individual."""
        if member:
            stats = player_stats.get(str(member.id), {"wins": 0, "losses": 0})
            total = stats["wins"] + stats["losses"]
            winrate = (stats["wins"] / total * 100) if total > 0 else 0
            await ctx.send(f"{member.display_name}'s winrate: {winrate:.2f}%")
        else:
            await ctx.send("Provide a player to check their winrate.")

    @commands.command(name="matchups")
    @has_role("high mage")
    async def matchups(self, ctx, team: str):
        """Suggests best matchups for the season (placeholder)."""
        await ctx.send(f"Generated matchups for {team}: 4x 3v3 and 8x 2v2.")

    @commands.command(name="activity")
    @has_role("high mage")
    async def activity(self, ctx, member: discord.Member = None):
        """Tracks activity of individuals (placeholder)."""
        await ctx.send(f"{member.display_name if member else 'Player'} has been active X days.")

    @commands.command(name="teamperformance")
    @has_role("high mage")
    async def team_performance(self, ctx, team: str):
        """Tracks performance of a team."""
        stats = team_stats.get(team, {"wins": 0, "losses": 0})
        await ctx.send(f"{team} - Wins: {stats['wins']} | Losses: {stats['losses']}")

    @commands.command(name="compare")
    @has_role("high mage")
    async def compare(self, ctx, member: discord.Member):
        """Compares individual performance to team performance."""
        player = player_stats.get(str(member.id), {"wins": 0, "losses": 0, "team": "None"})
        team = team_stats.get(player.get("team", "None"), {"wins": 0, "losses": 0})
        await ctx.send(f"{member.display_name} ({player['wins']}W/{player['losses']}L) vs Team {player.get('team', 'None')} ({team['wins']}W/{team['losses']}L)")

    @commands.command(name="settraining")
    @has_role("high mage")
    async def set_training(self, ctx, member: discord.Member, level: str):
        """Sets training level and updates roles."""
        if level.capitalize() not in TRAINING_ROLES:
            await ctx.send("Invalid training level. Choose Apprentice, Wizard, or Sage.")
            return

        # Remove old training roles
        for role_name in TRAINING_ROLES:
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            if role in member.roles:
                await member.remove_roles(role)

        # Add new training role
        new_role = discord.utils.get(ctx.guild.roles, name=level.capitalize())
        if new_role:
            await member.add_roles(new_role)
            player_stats.setdefault(str(member.id), {})["training_level"] = level.capitalize()
            save_data()
            await ctx.send(f"{member.display_name} is now {level.capitalize()}.")

    # ---------------- Spellkeeper Commands ---------------- #

    @commands.command(name="settimezone")
    @has_role("spellkeeper")
    async def set_timezone(self, ctx, member: discord.Member, tz_role: str):
        """Assigns a timezone role to a player."""
        timezones[str(member.id)] = tz_role
        save_data()
        await ctx.send(f"Timezone for {member.display_name} set to {tz_role}.")

    @commands.command(name="individualperf")
    @has_role("spellkeeper")
    async def individual_perf(self, ctx, member: discord.Member):
        """Checks individual performance."""
        stats = player_stats.get(str(member.id), {"wins": 0, "losses": 0})
        await ctx.send(f"{member.display_name} - Wins: {stats['wins']} | Losses: {stats['losses']}")

    @commands.command(name="teamperf")
    @has_role("spellkeeper")
    async def team_perf(self, ctx, team: str):
        """Checks team performance."""
        stats = team_stats.get(team, {"wins": 0, "losses": 0})
        await ctx.send(f"{team} - Wins: {stats['wins']} | Losses: {stats['losses']}")

    # ---------------- Special Listener for %initiate ---------------- #

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.content.startswith("%initiate"):
            parts = message.content.split()
            if len(parts) >= 3:
                member = message.mentions[0] if message.mentions else None
                if member:
                    apprentice_role = discord.utils.get(message.guild.roles, name="Apprentice")
                    if apprentice_role:
                        for role_name in TRAINING_ROLES:
                            role = discord.utils.get(message.guild.roles, name=role_name)
                            if role in member.roles:
                                await member.remove_roles(role)

                        await member.add_roles(apprentice_role)
                        player_stats.setdefault(str(member.id), {})["training_level"] = "Apprentice"
                        save_data()
                        await message.channel.send(f"{member.display_name} has been initiated as Apprentice!")
                    else:
                        await message.channel.send("No Apprentice role found in this server.")

async def setup(bot):
    await bot.add_cog(StatsBot(bot))
