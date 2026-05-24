import os
import sys
import asyncio
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands
from dotenv import load_dotenv

# =========================================================
# Import Persistent Views
# =========================================================

from cogs.help import HelpView
from cogs.modmail import (
    TicketCategoryView,
    OpenTicketButton
)

# =========================================================
# Base Directory
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

sys.path.insert(0, BASE_DIR)

load_dotenv()

# =========================================================
# Guild Configuration
# =========================================================

MAIN_GUILD_ID = int(
    os.getenv(
        "MAIN_GUILD_ID",
        "0"
    )
)

STAFF_GUILD_ID = int(
    os.getenv(
        "STAFF_GUILD_ID",
        "0"
    )
)

MAIN_GUILD = discord.Object(
    id=MAIN_GUILD_ID
)

STAFF_GUILD = discord.Object(
    id=STAFF_GUILD_ID
)

# =========================================================
# Bot Class Definition
# =========================================================

class BoltBot(commands.Bot):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

    async def setup_hook(self):

        # =====================================================
        # Load Cogs
        # =====================================================

        cogs_dir = os.path.join(
            BASE_DIR,
            "cogs"
        )

        if os.path.exists(cogs_dir):

            for filename in os.listdir(cogs_dir):

                if (
                    filename.endswith(".py")
                    and not filename.startswith("__")
                ):

                    cog_name = filename[:-3]

                    try:

                        await self.load_extension(
                            f"cogs.{cog_name}"
                        )

                        print(
                            f"[Extension] Loaded cog: "
                            f"cogs.{cog_name}"
                        )

                    except Exception as e:

                        print(
                            f"[Extension Fail] "
                            f"Error loading "
                            f"cogs.{cog_name}: {e}"
                        )

        # =====================================================
        # Staff Guild Sync
        # =====================================================

        if STAFF_GUILD_ID != 0:

            self.tree.copy_global_to(
                guild=STAFF_GUILD
            )

            staff_synced = await self.tree.sync(
                guild=STAFF_GUILD
            )

            print(
                f"✅ Synced "
                f"{len(staff_synced)} "
                f"staff guild commands."
            )

        # =====================================================
        # Main Guild Sync
        # =====================================================

        if MAIN_GUILD_ID != 0:

            self.tree.copy_global_to(
                guild=MAIN_GUILD
            )

            main_synced = await self.tree.sync(
                guild=MAIN_GUILD
            )

            print(
                f"✅ Synced "
                f"{len(main_synced)} "
                f"main guild commands."
            )

        # =====================================================
        # Global Sync
        # =====================================================

        global_synced = await self.tree.sync()

        print(
            f"✅ Synced "
            f"{len(global_synced)} "
            f"global commands."
        )

# =========================================================
# Web Server (Flask Keep Alive)
# =========================================================

app = Flask("")

@app.route("/")
def home():

    return (
        "Bolt Multi-Server Engine "
        "is alive and responsive."
    )

def run_flask():

    port = int(
        os.getenv(
            "PORT",
            8080
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )

def start_web_server():

    t = Thread(
        target=run_flask
    )

    t.start()

    print(
        "[Web Engine] "
        "Flask server thread started."
    )

# =========================================================
# Dynamic Prefix Resolver
# =========================================================

async def get_prefix(bot, message):

    if message.author.id in bot.DEVELOPER_IDS:

        return "!"

    if not message.guild:

        return "!"

    for cog_name in [

        "DatabaseCog",
        "DatabaseHandler",
        "Database"

    ]:

        db_cog = bot.get_cog(
            cog_name
        )

        if (
            db_cog
            and hasattr(
                db_cog,
                "get_guild_prefix"
            )
        ):

            custom_prefix = await db_cog.get_guild_prefix(
                message.guild.id
            )

            if custom_prefix:

                return custom_prefix

    return "!"

# =========================================================
# Bot Initialization
# =========================================================

intents = discord.Intents.all()

bot = BoltBot(

    command_prefix=get_prefix,

    intents=intents,

    help_command=None
)

# =========================================================
# Developer IDs
# =========================================================

bot.DEVELOPER_IDS = [

    int(dev_id.strip())

    for dev_id in os.getenv(
        "DEVELOPER_IDS",
        ""
    ).split(",")

    if dev_id.strip().isdigit()
]

print(
    f"[Developers] Loaded "
    f"{len(bot.DEVELOPER_IDS)} "
    f"developer IDs."
)

# =========================================================
# Global Blacklist Check
# =========================================================

@bot.check
async def global_blacklist_check(ctx):

    if ctx.author.id in bot.DEVELOPER_IDS:

        return True

    db_cog = bot.get_cog(
        "DatabaseCog"
    )

    if not db_cog:

        return True

    user_blacklist = await db_cog.blacklist.find_one({

        "_id": str(ctx.author.id),
        "type": "user"

    })

    if user_blacklist:

        return False

    if ctx.guild:

        guild_blacklist = await db_cog.blacklist.find_one({

            "_id": str(ctx.guild.id),
            "type": "guild"

        })

        if guild_blacklist:

            try:

                await ctx.guild.leave()

            except Exception:

                pass

            return False

    return True

# =========================================================
# Ready Event
# =========================================================

@bot.event
async def on_ready():

    print("==================================================")

    print(
        f"[Initialization] "
        f"Logged in as: "
        f"{bot.user.name} ({bot.user.id})"
    )

    print(
        "[Initialization] "
        "System architecture loaded cleanly."
    )

    print("==================================================")

    guild_count = len(
        bot.guilds
    )

    activity_text = (
        f"over {guild_count} servers "
        f"| Bolt Engine"
    )

    await bot.change_presence(

        status=discord.Status.online,

        activity=discord.Activity(

            type=discord.ActivityType.watching,

            name=activity_text
        ),
    )

    # =====================================================
    # Restore Persistent Views
    # =====================================================

    try:

        bot.add_view(
            HelpView()
        )

        bot.add_view(
            TicketCategoryView(bot)
        )

        bot.add_view(
            OpenTicketButton()
        )

        print(
            "[Views] Persistent views "
            "restored successfully."
        )

    except Exception as e:

        print(
            f"[Views Fail] "
            f"Failed restoring "
            f"persistent views: {e}"
        )

    # =====================================================
    # Restore Database Persistent Views
    # =====================================================

    for cog_name in [

        "DatabaseCog",
        "DatabaseHandler",
        "Database"

    ]:

        db_cog = bot.get_cog(
            cog_name
        )

        if (
            db_cog
            and hasattr(
                db_cog,
                "restore_persistent_views"
            )
        ):

            try:

                await db_cog.restore_persistent_views()

                print(
                    "[Database] Persistent "
                    "database views restored."
                )

            except Exception as e:

                print(
                    f"[Database Fail] "
                    f"Persistent view "
                    f"restoration failed: {e}"
                )

            break

    print("==================================================")

    print(
        "[System Ready] "
        "Bolt Engine is fully operational."
    )

    print("==================================================")

# =========================================================
# Global Error Handler
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(
        error,
        commands.CommandNotFound
    ):

        return

    raise error

# =========================================================
# Main Startup
# =========================================================

async def main():

    # =====================================================
    # Start Flask Server
    # =====================================================

    start_web_server()

    async with bot:

        token = (
            os.getenv("BOT_TOKEN")
            or os.getenv("DISCORD_TOKEN")
        )

        if not token:

            raise ValueError(
                "CRITICAL ERROR: "
                "No token found."
            )

        await bot.start(token)

if __name__ == "__main__":

    asyncio.run(main())
