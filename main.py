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


# ---------------------------------------------------------------------------
# Web server for Render port binding to keep the service alive
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Dynamic prefix resolver
# ---------------------------------------------------------------------------

async def get_prefix(bot, message):
    # Developers always get the default prefix regardless of guild settings
    if message.author.id in bot.DEVELOPER_IDS:
        return "!"

    if not message.guild:
        return "!"

    # Support multiple cog naming conventions
    for cog_name in ["DatabaseCog", "DatabaseHandler", "Database"]:
        db_cog = bot.get_cog(cog_name)
        if db_cog and hasattr(db_cog, "get_guild_prefix"):
            custom_prefix = await db_cog.get_guild_prefix(message.guild.id)
            if custom_prefix:
                return custom_prefix
    return "!"


# ---------------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)

# Hardcoded developer IDs — full system override authority
bot.DEVELOPER_IDS = [1503347550122410065]


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@bot.event
async def on_ready():
    print("==================================================")
    print(f"[Initialization] Logged in as: {bot.user.name} ({bot.user.id})")
    print("[Initialization] System architecture loaded cleanly.")
    print("==================================================")

    # Dynamic presence reflecting current guild count
    guild_count = len(bot.guilds)
    activity_text = f"over {guild_count} servers | Bolt Engine"
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=discord.ActivityType.watching, name=activity_text),
    )
    print(f"[Presence] Dynamic activity set to: Watching {activity_text}")

    # Global slash-command synchronization
    try:
        print("[Sync] Initializing application commands sync...")
        synced = await bot.tree.sync()
        print(f"[Sync Success] Synchronized {len(synced)} slash commands globally.")
    except discord.HTTPException as http_err:
        print(f"[Sync Fail] Discord API HTTP error during auto-sync: {http_err}")
    except Exception as e:
        print(f"[Sync Fail] Unexpected error during auto-sync: {e}")

    # Restore persistent views (buttons/dropdowns) after reboot
    for cog_name in ["DatabaseCog", "DatabaseHandler", "Database"]:
        db_cog = bot.get_cog(cog_name)
        if db_cog and hasattr(db_cog, "restore_persistent_views"):
            await db_cog.restore_persistent_views()
            break


@bot.event
async def on_command_error(ctx, error):
    """Global prefix-command error handler — prevents unhandled error noise in logs."""
    if isinstance(error, commands.CommandNotFound):
        return  # Silently ignore unknown prefix commands
    raise error


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    async with bot:
        # Load all cogs from the /cogs directory
        cogs_dir = os.path.join(BASE_DIR, "cogs")
        if os.path.exists(cogs_dir):
            # Sort to ensure database cog loads first
            filenames = sorted(os.listdir(cogs_dir))
            for filename in filenames:
                if filename.endswith(".py") and not filename.startswith("__"):
                    cog_name = filename[:-3]
                    try:
                        await bot.load_extension(f"cogs.{cog_name}")
                        print(f"[Extension] Loaded cog: cogs.{cog_name}")
                    except Exception as e:
                        print(f"[Extension Fail] Error loading cogs.{cog_name}: {e}")
        else:
            print(f"[Critical Error] Cogs directory not found at: {cogs_dir}")

        await start_web_server()

        # Support both common token env-var names
        token = os.getenv("BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
        if not token:
            raise ValueError(
                "CRITICAL ERROR: Neither BOT_TOKEN nor DISCORD_TOKEN found in environment variables."
            )
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
