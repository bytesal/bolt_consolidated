import os
import sys
import asyncio
from aiohttp import web
import discord
from discord.ext import commands
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

load_dotenv()

# Web server for Render Port binding to keep service active
async def handle_ping(request):
    return web.Response(text="Bolt Multi-Server Engine is alive and responsive.")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[Web Engine] Port binding active on 0.0.0.0:{port}")

async def get_prefix(bot, message):
    if message.author.id in bot.DEVELOPER_IDS:
        return "!"
        
    if not message.guild:
        return "!"
        
    # Check for database custom prefix securely across common cog name variants
    for cog_name in ["DatabaseCog", "DatabaseHandler", "Database"]:
        db_cog = bot.get_cog(cog_name)
        if db_cog and hasattr(db_cog, "get_guild_prefix"):
            custom_prefix = await db_cog.get_guild_prefix(message.guild.id)
            if custom_prefix:
                return custom_prefix
    return "!"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)

# Hardcoded Developer IDs (Full system override authority)
bot.DEVELOPER_IDS = [1503347550122410065]

@bot.event
async def on_ready():
    print(f"==================================================")
    print(f"[Initialization] Logged in as: {bot.user.name} ({bot.user.id})")
    print(f"[Initialization] System Architecture Loaded Cleanly.")
    print(f"==================================================")
    
    # Setting up an advanced dynamic presence for the multi-server nature of the bot
    guild_count = len(bot.guilds)
    activity_text = f"over {guild_count} servers | Bolt Engine"
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=discord.ActivityType.watching, name=activity_text)
    )
    print(f"[Presence] Dynamic activity successfully set to: Watching {activity_text}")
    
    # Automatic global command synchronization on startup
    try:
        print("[Sync] Initializing automatic application commands sync...")
        synced = await bot.tree.sync()
        print(f"[Sync Success] Automatically synchronized {len(synced)} slash commands globally.")
    except discord.HTTPException as http_err:
        print(f"[Sync Fail] Discord API HTTP error during auto-sync: {http_err}")
    except Exception as e:
        print(f"[Sync Fail] Unexpected system error during auto-sync: {e}")

    # Persistent View restoration across reboots
    for cog_name in ["DatabaseCog", "DatabaseHandler", "Database"]:
        db_cog = bot.get_cog(cog_name)
        if db_cog and hasattr(db_cog, "restore_persistent_views"):
            await db_cog.restore_persistent_views()
            break

async def main():
    async with bot:
        # Step 1: Securely dynamic loading of all files within the cogs directory
        cogs_dir = os.path.join(BASE_DIR, "cogs")
        if os.path.exists(cogs_dir):
            for filename in os.listdir(cogs_dir):
                if filename.endswith(".py") and not filename.startswith("__"):
                    cog_name = filename[:-3]
                    try:
                        await bot.load_extension(f"cogs.{cog_name}")
                        print(f"[Extension] Successfully attached dynamic cog: cogs.{cog_name}")
                    except Exception as e:
                        print(f"[Extension Fail] Dynamic critical loading error in cogs.{cog_name}: {e}")
        else:
            print(f"[Critical Error] Target cogs directory path not resolved at: {cogs_dir}")
                
        await start_web_server()
        
        # Checking both common environment variable names for consistency
        token = os.getenv("BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
        if not token:
            raise ValueError("CRITICAL ERROR: Neither BOT_TOKEN nor DISCORD_TOKEN was found in the environment variables.")
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
