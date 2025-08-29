import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.members = True  # needed to add/remove roles
intents.message_content = True

bot = commands.Bot(command_prefix="<", intents=intents)

async def setup_hook():
    await bot.load_extension("commands")  # loads commands.py

bot.setup_hook = setup_hook

bot.run(os.getenv("DISCORD_TOKEN"))
