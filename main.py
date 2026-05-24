import os
import sys
import asyncio
from aiohttp import web
import discord
from discord.ext import commands
from dotenv import load_dotenv

# =========================================================
# Import Persistent Views
# =========================================================

from cogs.help import HelpView
from cogs.modmail import TicketCategoryView

# =========================================================
# Base Directory
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

load_dotenv()

# =========================================================
# Web Server (Render Keep Alive)
# =========================================================

async def handle_ping(request):
    return web.Response(
        text="Bolt Multi-Server Engine is alive and responsive."
    )


async def start_web_server():

    app = web.Application()

    app.router.add_get("/", handle_ping)

    runner = web.AppRunner(app)

    await runner.setup()

    port = int(os.getenv("PORT", 8080))

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    print(
        f"[Web Engine] Port binding active on 0.0.0.0:{port}"
    )

# =========================================================
# Dynamic Prefix Resolver
# =========================================================

async def get_prefix(bot, message):

    # Developers always bypass guild prefixes
    if message.author.id in bot.DEVELOPER_IDS:
        return "!"

    # DMs always use default prefix
    if not message.guild:
        return "!"

    # Search for database cog
    for cog_name in [
        "DatabaseCog",
        "DatabaseHandler",
        "Database"
    ]:

        db_cog = bot.get_cog(cog_name)

        if (
            db_cog
            and hasattr(db_cog, "get_guild_prefix")
        ):

            custom_prefix = await db_cog.get_guild_prefix(
                message.guild.id
            )

            if custom_prefix:
                return custom_prefix

    return "!"

# =========================================================
# Discord Intents
# =========================================================

intents = discord.Intents.all()

# =========================================================
# Bot Initialization
# =========================================================

bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None
)

# =========================================================
# Developer IDs
# =========================================================

bot.DEVELOPER_IDS = [
    1503347550122410065
]

# =========================================================
# Ready Event
# =========================================================

@bot.event
async def on_ready():

    print("==================================================")
    print(
        f"[Initialization] Logged in as: "
        f"{bot.user.name} ({bot.user.id})"
    )
    print(
        "[Initialization] System architecture loaded cleanly."
    )
    print("==================================================")

    # =====================================================
    # Dynamic Presence
    # =====================================================

    guild_count = len(bot.guilds)

    activity_text = (
        f"over {guild_count} servers | Bolt Engine"
    )

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=activity_text
        ),
    )

    print(
        f"[Presence] Dynamic activity set to: "
        f"Watching {activity_text}"
    )

    # =====================================================
    # Slash Command Sync
    # =====================================================

    try:

        print(
            "[Sync] Initializing application commands sync..."
        )

        synced = await bot.tree.sync()

        print(
            f"[Sync Success] "
            f"Synchronized {len(synced)} slash commands globally."
        )

    except discord.HTTPException as http_err:

        print(
            f"[Sync Fail] "
            f"Discord API HTTP error during auto-sync: "
            f"{http_err}"
        )

    except Exception as e:

        print(
            f"[Sync Fail] "
            f"Unexpected error during auto-sync: {e}"
        )

    # =====================================================
    # Restore Persistent Views
    # =====================================================

    try:

        bot.add_view(HelpView())

        bot.add_view(
            TicketCategoryView(bot)
        )

        print(
            "[Views] Persistent views restored successfully."
        )

    except Exception as e:

        print(
            f"[Views Fail] "
            f"Failed restoring persistent views: {e}"
        )

    # =====================================================
    # Restore Database Persistent Views
    # =====================================================

    for cog_name in [
        "DatabaseCog",
        "DatabaseHandler",
        "Database"
    ]:

        db_cog = bot.get_cog(cog_name)

        if (
            db_cog
            and hasattr(db_cog, "restore_persistent_views")
        ):

            try:

                await db_cog.restore_persistent_views()

                print(
                    "[Database] "
                    "Persistent database views restored."
                )

            except Exception as e:

                print(
                    f"[Database Fail] "
                    f"Persistent view restoration failed: {e}"
                )

            break

    print("==================================================")
    print("[System Ready] Bolt Engine is fully operational.")
    print("==================================================")


# =========================================================
# Global Error Handler
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    # Ignore unknown prefix commands
    if isinstance(error, commands.CommandNotFound):
        return

    raise error

# =========================================================
# Main Startup
# =========================================================

async def main():

    async with bot:

        # =================================================
        # Load All Cogs
        # =================================================

        cogs_dir = os.path.join(BASE_DIR, "cogs")

        if os.path.exists(cogs_dir):

            filenames = sorted(
                os.listdir(cogs_dir)
            )

            for filename in filenames:

                if (
                    filename.endswith(".py")
                    and not filename.startswith("__")
                ):

                    cog_name = filename[:-3]

                    try:

                        await bot.load_extension(
                            f"cogs.{cog_name}"
                        )

                        print(
                            f"[Extension] Loaded cog: "
                            f"cogs.{cog_name}"
                        )

                    except Exception as e:

                        print(
                            f"[Extension Fail] "
                            f"Error loading cogs.{cog_name}: {e}"
                        )

        else:

            print(
                f"[Critical Error] "
                f"Cogs directory not found at: {cogs_dir}"
            )

        # =================================================
        # Start Web Server
        # =================================================

        await start_web_server()

        # =================================================
        # Load Token
        # =================================================

        token = (
            os.getenv("BOT_TOKEN")
            or os.getenv("DISCORD_TOKEN")
        )

        if not token:

            raise ValueError(
                "CRITICAL ERROR: "
                "Neither BOT_TOKEN nor DISCORD_TOKEN "
                "found in environment variables."
            )

        # =================================================
        # Start Bot
        # =================================================

        await bot.start(token)

# =========================================================
# Entrypoint
# =========================================================

if __name__ == "__main__":
    asyncio.run(main())
