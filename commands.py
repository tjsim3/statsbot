import discord
from discord.ext import commands
from discord.ext.commands import has_role
import json
import os
import time


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
    @commands.command(name="upload")
    @has_role("high mage")  # Only high mage can add players
    async def upload(self, ctx, member: discord.Member):
        """
        Upload a new player to the stats system.
        Usage: <upload @player
        """
        pid = str(member.id)
        if pid in player_stats:
            await ctx.send(f"⚠ {member.display_name} is already uploaded.")
            return
    
        # Initialize player stats
        player_stats[pid] = {
            "wins": 0,
            "losses": 0,
            "team": "None",
            "training_level": "None"
        }
        save_data()
        await ctx.send(f"✅ {member.display_name} has been uploaded to the stats system.")

    @commands.command(name="record")
    @has_role("high mage")  # Only high mage can record matches
    async def record(self, ctx, result: str, player: discord.Member, *teammates: discord.Member):
        """
        Records a win or loss for a player and optionally their team.
        Usage: <record w @player [@teammate1 @teammate2]
               <record l @player [@teammate1 @teammate2]
        Only players uploaded with <upload can be recorded.
        """
    
        result = result.lower()
        if result not in ["w", "l"]:
            await ctx.send("❌ Invalid result. Use 'w' for win or 'l' for loss.")
            return
    
        # Combine player and teammates
        team_members = [player] + list(teammates)
    
        # Check that all players are uploaded
        for m in team_members:
            if str(m.id) not in player_stats:
                await ctx.send(f"❌ {m.display_name} is not uploaded. Use `<upload` first.")
                return
    
        # Update individual stats
        for m in team_members:
            pid = str(m.id)
            if result == "w":
                player_stats[pid]["wins"] += 1
            else:
                player_stats[pid]["losses"] += 1
    
        # Construct team name from members
        team_name = "-".join([m.display_name for m in team_members])
    
        # Update team stats
        team_stats.setdefault(team_name, {"wins": 0, "losses": 0, "games_played": 0})
        if result == "w":
            team_stats[team_name]["wins"] += 1
        else:
            team_stats[team_name]["losses"] += 1
        team_stats[team_name]["games_played"] += 1
    
        # Update each member's team info
        for m in team_members:
            player_stats[str(m.id)]["team"] = team_name
    
        # Save changes
        save_data()
    
        # Respond in Discord
        await ctx.send(f"✅ Recorded {'win' if result=='w' else 'loss'} for {', '.join([m.display_name for m in team_members])} (Team: {team_name}).")

    
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

    @commands.command(name="listplayers")
    @has_role("Spellkeeper")  # Only high mage can use this
    async def list_players(self, ctx):
        """
        Lists all uploaded players with their team and training role.
        Usage: <listplayers
        """
        if not player_stats:
            await ctx.send("⚠ No players have been uploaded yet.")
            return
    
        # Build the list message
        lines = ["**Uploaded Players:**"]
        for pid, stats in player_stats.items():
            member = ctx.guild.get_member(int(pid))
            name = member.display_name if member else f"Unknown ({pid})"
            team = stats.get("team", "None")
            role = stats.get("training_level", "None")
            lines.append(f"- {name} | Team: {team} | Role: {role}")
    
        # Send in chunks if too long
        message = "\n".join(lines)
        if len(message) > 2000:  # Discord message limit
            for chunk_start in range(0, len(message), 1900):
                await ctx.send("```\n" + message[chunk_start:chunk_start+1900] + "\n```")
        else:
            await ctx.send("```\n" + message + "\n```")


    @commands.command(name="ping")
    async def ping(self, ctx):
        """Shows bot latency"""
        latency = round(self.bot.latency * 1000)  # convert to ms
        await ctx.send(f"🏓 Pong! Latency: {latency}ms")

    @commands.command(name="settimezone")
    @has_role("Spellkeeper")
    async def set_timezone(self, ctx, member: discord.Member, tz_role: str):
        """Assigns a timezone role to a player."""
        timezones[str(member.id)] = tz_role
        save_data()
        await ctx.send(f"Timezone for {member.display_name} set to {tz_role}.")

    @commands.command(name="individualperf")
    @has_role("Spellkeeper")
    async def individual_perf(self, ctx, member: discord.Member):
        """Checks individual performance."""
        stats = player_stats.get(str(member.id), {"wins": 0, "losses": 0})
        await ctx.send(f"{member.display_name} - Wins: {stats['wins']} | Losses: {stats['losses']}")

    @commands.command(name="teamperf")
    @has_role("Spellkeeper")
    async def team_perf(self, ctx, team: str):
        """Checks team performance."""
        stats = team_stats.get(team, {"wins": 0, "losses": 0})
        await ctx.send(f"{team} - Wins: {stats['wins']} | Losses: {stats['losses']}")

    # ---------------- Special Listener for %initiate ---------------- #

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
    
        # Ignore normal commands to prevent double processing
        if message.content.startswith(self.bot.command_prefix):
            return
    
        # Handle %initiate only
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


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # Only respond if the message starts with your command prefix
        if not ctx.message.content.startswith("<"):
            return
    
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"⚠ Missing argument: {error.param}")
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send(f"❌ Unknown command. Try `<ping` or another valid command.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You do not have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have permission to do that.")
        else:
            await ctx.send(f"❌ An unexpected error occurred: `{error}`")
            raise error  # optional: log full traceback


async def setup(bot):
    await bot.add_cog(StatsBot(bot))
