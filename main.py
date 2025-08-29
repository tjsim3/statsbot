import discord
from discord.ext import commands
import os

# import your commands extension
from commands import setup_commands

# Intents are required for member events
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create bot with prefix "<"
bot = commands.Bot(command_prefix="<", intents=intents)

# Load all commands from commands.py
setup_commands(bot)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

# Run bot (expects DISCORD_TOKEN environment variable)
bot.run(os.getenv("DISCORD_TOKEN"))
