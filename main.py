import discord
from discord.ext import commands
import os
from dotenv import load_dotenv



intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="<", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

# Properly load the commands cog synchronously before bot.run()
async def setup():
    await bot.load_extension("commands")  # loads commands.py as a Cog

# Use Discord token from Railway environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Run bot with the async setup
async def main():
    async with bot:
        await setup()
        await bot.start(TOKEN)

import asyncio
asyncio.run(main())
