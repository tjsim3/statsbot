import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="<", intents=intents)

# ============ CHANNEL RESTRICTION ============
ALLOWED_CHANNEL_IDS = [
    int(id.strip()) 
    for id in os.getenv('ALLOWED_CHANNEL_IDS', '').split(',') 
    if id.strip()
]

@bot.check
async def globally_block_channels(ctx):
    """Block all commands outside allowed channels"""
    if not ALLOWED_CHANNEL_IDS:
        # If no channels configured, allow all (for testing)
        return True
    
    if ctx.channel.id not in ALLOWED_CHANNEL_IDS:
        await ctx.send(f"❌ This bot only works in designated team management channels!")
        return False
    return True
# =============================================

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    if ALLOWED_CHANNEL_IDS:
        print(f"🔒 Bot restricted to {len(ALLOWED_CHANNEL_IDS)} channel(s)")
    else:
        print("⚠️ No channel restrictions (set ALLOWED_CHANNEL_IDS in .env)")
    print("------")

# Properly load the commands cog synchronously before bot.run()
async def setup():
    await bot.load_extension("commands")  # loads commands.py as a Cog

# Use Discord token from Railway environment variables
TOKEN = os.getenv("DISCORD_TOKEN")

# Run bot with the async setup
async def main():
    async with bot:
        await setup()
        await bot.start(TOKEN)

import asyncio
asyncio.run(main())