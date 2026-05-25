import os
import sys
import asyncio
import signal
import threading
from flask import Flask
from werkzeug.serving import make_server
from discord.ext import commands
import discord
from dotenv import load_dotenv

# ------------------------------------------------------------
# Base Directory & Environment
# ------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
load_dotenv()

# ------------------------------------------------------------
# Guild Configuration
# ------------------------------------------------------------

MAIN_GUILD_ID = int(os.getenv("MAIN_GUILD_ID", "0"))
STAFF_GUILD_ID = int(os.getenv("STAFF_GUILD_ID", "0"))

MAIN_GUILD = discord.Object(id=MAIN_GUILD_ID) if MAIN_GUILD_ID else None
STAFF_GUILD = discord.Object(id=STAFF_GUILD_ID) if STAFF_GUILD_ID else None

# ------------------------------------------------------------
# Flask Keep‑Alive Server (Threaded)
# ------------------------------------------------------------

flask_app = Flask("")
flask_thread = None

@flask_app.route("/")
def home():
    return "Bolt Multi-Server Engine is alive and responsive."

def run_flask():
    port = int(os.getenv("PORT", 8080))
    server = make_server("0.0.0.0", port, flask_app)
    server.serve_forever()

def start_flask():
    global flask_thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("[Web Engine] Flask server thread started.")

def stop_flask():
    print("[Web Engine] Flask server stopping...")

# ------------------------------------------------------------
# Dynamic Prefix Resolver
# ------------------------------------------------------------

async def get_prefix(bot, message):
    if message.author.id in bot.DEVELOPER_IDS:
        return "!"
    if not message.guild:
        return "!"
    db_cog = bot.get_cog("DatabaseCog")
    if db_cog and hasattr(db_cog, "get_guild_prefix"):
        custom_prefix = await db_cog.get_guild_prefix(message.guild.id)
        if custom_prefix:
            return custom_prefix
    return "!"

# ------------------------------------------------------------
# Bot Class Definition
# ------------------------------------------------------------

class BoltBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ready_flag = False

    async def setup_hook(self):
        """Called once when the bot starts – load cogs, sync commands, restore views."""
        print("[Hook] setup_hook started.")

        # 1. Load cogs
        cogs_dir = os.path.join(BASE_DIR, "cogs")
        if os.path.exists(cogs_dir):
            for filename in sorted(os.listdir(cogs_dir)):
                if filename.endswith(".py") and not filename.startswith("__"):
                    cog_name = filename[:-3]
                    try:
                        await self.load_extension(f"cogs.{cog_name}")
                        print(f"[Extension] Loaded cog: cogs.{cog_name}")
                    except Exception as e:
                        print(f"[Extension Fail] cogs.{cog_name}: {e}")

        # 2. Register static persistent views (must be done before sync)
        self._add_static_views()

        # 3. Restore dynamic database‑backed views
        db_cog = self.get_cog("DatabaseCog")
        if db_cog and hasattr(db_cog, "restore_persistent_views"):
            try:
                await db_cog.restore_persistent_views()
                print("[Database] Persistent views restored.")
            except Exception as e:
                print(f"[Database Fail] Persistent view restoration failed: {e}")

        # 4. Ensure database indexes (new Phase 4)
        if db_cog and hasattr(db_cog, "ensure_indexes"):
            try:
                await db_cog.ensure_indexes()
                print("[Database] Indexes created/verified.")
            except Exception as e:
                print(f"[Database] Index creation failed: {e}")

        # 5. Sync slash commands
        await self._sync_commands()

        print("[Hook] setup_hook completed.")

    def _add_static_views(self):
        """Add views that do not depend on database data."""
        try:
            from cogs.help import HelpView
            self.add_view(HelpView())
            print("[Views] HelpView registered.")
        except Exception as e:
            print(f"[Views Fail] HelpView: {e}")

        try:
            from cogs.modmail import TicketCategoryView, OpenTicketButton
            self.add_view(TicketCategoryView(self))
            self.add_view(OpenTicketButton())
            print("[Views] Modmail views registered.")
        except Exception as e:
            print(f"[Views Fail] Modmail views: {e}")

    async def _sync_commands(self):
        """Sync commands to guilds and globally."""
        if STAFF_GUILD_ID != 0 and STAFF_GUILD:
            self.tree.copy_global_to(guild=STAFF_GUILD)
            synced = await self.tree.sync(guild=STAFF_GUILD)
            print(f"✅ Synced {len(synced)} staff guild commands.")

        if MAIN_GUILD_ID != 0 and MAIN_GUILD:
            self.tree.copy_global_to(guild=MAIN_GUILD)
            synced = await self.tree.sync(guild=MAIN_GUILD)
            print(f"✅ Synced {len(synced)} main guild commands.")

        synced = await self.tree.sync()
        print(f"✅ Synced {len(synced)} global commands.")

    async def on_ready(self):
        if not self._ready_flag:
            self._ready_flag = True
            print("=" * 50)
            print(f"[Initialization] Logged in as: {self.user.name} ({self.user.id})")
            print("[Initialization] System architecture loaded cleanly.")
            print("=" * 50)

        guild_count = len(self.guilds)
        activity_text = f"over {guild_count} servers | Bolt Engine"
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=activity_text
            )
        )

        if self._ready_flag:
            print("[System Ready] Bolt Engine is fully operational.")
            print("=" * 50)

    async def close(self):
        print("[Shutdown] Closing bot connections...")
        stop_flask()
        await super().close()
        print("[Shutdown] Bot closed.")

# ------------------------------------------------------------
# Developer IDs & Global Blacklist Check
# ------------------------------------------------------------

intents = discord.Intents.all()
bot = BoltBot(command_prefix=get_prefix, intents=intents, help_command=None)

bot.DEVELOPER_IDS = [
    int(dev_id.strip())
    for dev_id in os.getenv("DEVELOPER_IDS", "").split(",")
    if dev_id.strip().isdigit()
]
print(f"[Developers] Loaded {len(bot.DEVELOPER_IDS)} developer IDs.")

@bot.check
async def global_blacklist_check(ctx):
    if ctx.author.id in bot.DEVELOPER_IDS:
        return True
    db_cog = bot.get_cog("DatabaseCog")
    if not db_cog:
        return True
    user_blacklist = await db_cog.blacklist.find_one({"_id": str(ctx.author.id), "type": "user"})
    if user_blacklist:
        return False
    if ctx.guild:
        guild_blacklist = await db_cog.blacklist.find_one({"_id": str(ctx.guild.id), "type": "guild"})
        if guild_blacklist:
            try:
                await ctx.guild.leave()
            except Exception:
                pass
            return False
    return True

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    raise error

# ------------------------------------------------------------
# Signal Handling for Graceful Shutdown
# ------------------------------------------------------------

def handle_shutdown_signal(signum, frame):
    print(f"\n[Signal] Received {signal.Signals(signum).name}. Shutting down gracefully...")
    asyncio.create_task(bot.close())

signal.signal(signal.SIGTERM, handle_shutdown_signal)
signal.signal(signal.SIGINT, handle_shutdown_signal)

# ------------------------------------------------------------
# Main Entry Point
# ------------------------------------------------------------

async def main():
    start_flask()
    token = os.getenv("BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("CRITICAL ERROR: No bot token found.")
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
