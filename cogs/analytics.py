import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import time
from utils.logger import get_logger

logger = get_logger("analytics")


class AnalyticsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    def format_uptime(self):
        seconds = int(time.time() - self.start_time)
        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        return f"{days}d {hours}h {minutes}m {seconds}s"

    @app_commands.command(name="dashboard", description="View bot analytics dashboard.")
    async def dashboard(self, interaction: discord.Interaction):
        logger.info(f"/dashboard used by {interaction.user} (ID: {interaction.user.id})")
        await interaction.response.defer()  # <-- CRITICAL: prevents timeout

        try:
            db_cog = self.bot.get_cog("DatabaseCog")
            if not db_cog or not db_cog.db:
                await interaction.followup.send("❌ DatabaseCog is not loaded or database not connected.", ephemeral=True)
                return

            # Counts
            guild_count = len(self.bot.guilds)
            user_count = sum(guild.member_count or 0 for guild in self.bot.guilds)
            total_cases = await db_cog.mod_cases.count_documents({})
            total_tickets = await db_cog.modmail_tickets.count_documents({})
            ping = round(self.bot.latency * 1000)
            uptime = self.format_uptime()

            # Top staff
            top_staff_cursor = db_cog.mod_cases.aggregate([
                {"$group": {"_id": "$issuer_name", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 5}
            ])
            top_staff = []
            async for staff in top_staff_cursor:
                top_staff.append(f"• {staff['_id']} — {staff['count']} actions")
            if not top_staff:
                top_staff = ["No moderation data."]

            embed = discord.Embed(
                title="📊 Bolt Analytics Dashboard",
                color=discord.Color.blurple(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="🌐 Servers", value=str(guild_count), inline=True)
            embed.add_field(name="👥 Users", value=str(user_count), inline=True)
            embed.add_field(name="⚡ Ping", value=f"{ping}ms", inline=True)
            embed.add_field(name="🛡️ Mod Cases", value=str(total_cases), inline=True)
            embed.add_field(name="🎫 Tickets", value=str(total_tickets), inline=True)
            embed.add_field(name="⏳ Uptime", value=uptime, inline=True)
            embed.add_field(name="👮 Top Staff", value="\n".join(top_staff), inline=False)
            embed.set_footer(text="Bolt Multi-Server Engine")

            await interaction.followup.send(embed=embed)
            logger.info("/dashboard completed successfully")

        except Exception as e:
            logger.error(f"/dashboard failed: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred while generating the dashboard.", ephemeral=True)

    @app_commands.command(name="botstats", description="View detailed bot statistics.")
    async def botstats(self, interaction: discord.Interaction):
        logger.info(f"/botstats used by {interaction.user}")
        # This command is simple, but still defer to be safe
        await interaction.response.defer()
        try:
            embed = discord.Embed(
                title="🤖 Bot Statistics",
                color=discord.Color.green()
            )
            embed.add_field(name="Servers", value=str(len(self.bot.guilds)))
            embed.add_field(name="Commands", value=str(len(self.bot.tree.get_commands())))
            embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms")
            embed.add_field(name="Uptime", value=self.format_uptime(), inline=False)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"/botstats failed: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AnalyticsCog(bot))
