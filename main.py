import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="<", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

# Load commands cog
async def load_cogs():
    await bot.load_extension("commands")  # this loads commands.py as a cog

bot.loop.create_task(load_cogs())

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
