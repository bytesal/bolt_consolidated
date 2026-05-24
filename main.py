import os
import asyncio
from aiohttp import web
import discord
from discord.ext import commands
from dotenv import load_dotenv

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
    if not message.guild:
        return "!"
    db_cog = bot.get_cog("DatabaseCog")
    if db_cog:
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
    
    # Persistent View restoration across reboots
    db_cog = bot.get_cog("DatabaseCog")
    if db_cog:
        await db_cog.restore_persistent_views()

async def main():
    async with bot:
        # Load DB engine first before structural extensions
        await bot.load_extension("cogs.database")
        
        extensions = [
            "cogs.core",
            "cogs.leveling",
            "cogs.reception",
            "cogs.applications",
            "cogs.modmail",
            "cogs.moderation",
            "cogs.sticky",
            "cogs.staff_quota"
        ]
        for ext in extensions:
            try:
                await bot.load_extension(ext)
                print(f"[Extension] Successfully attached {ext}")
            except Exception as e:
                print(f"[Extension Fail] Critical loading error in {ext}: {e}")
                
        await start_web_server()
        token = os.getenv("BOT_TOKEN")
        if not token:
            raise ValueError("CRITICAL ERROR: BOT_TOKEN is missing in the environment variables.")
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
