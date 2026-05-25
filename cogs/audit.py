import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import json


class AuditCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def log_audit(self, guild_id: int, action: str, actor_id: int, actor_name: str,
                        target_id: int = None, target_name: str = None,
                        details: dict = None, severity: str = "info"):
        """Log an audit entry to database and optional Discord channel."""
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return
        entry = {
            "guild_id": str(guild_id),
            "action": action,
            "actor_id": str(actor_id),
            "actor_name": actor_name,
            "target_id": str(target_id) if target_id else None,
            "target_name": target_name,
            "details": details or {},
            "severity": severity,
            "timestamp": datetime.utcnow()
        }
        await db_cog.audit_log.insert_one(entry)

        # Optional: send to a Discord audit channel if configured
        config = await db_cog.settings.find_one({"_id": f"audit_channel_{guild_id}"})
        if config:
            channel = self.bot.get_channel(int(config["value"]))
            if channel:
                embed = discord.Embed(
                    title=f"📋 Audit: {action}",
                    color=discord.Color.dark_blue() if severity == "info" else discord.Color.orange(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Actor", value=f"{actor_name} (`{actor_id}`)", inline=False)
                if target_id:
                    embed.add_field(name="Target", value=f"{target_name or target_id} (`{target_id}`)", inline=False)
                if details:
                    embed.add_field(name="Details", value=json.dumps(details, indent=2)[:1024], inline=False)
                await channel.send(embed=embed)

    @app_commands.command(name="setauditchannel", description="Set the channel for audit log notifications.")
    @app_commands.default_permissions(administrator=True)
    async def set_audit_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)
        await db_cog.settings.update_one(
            {"_id": f"audit_channel_{interaction.guild.id}"},
            {"$set": {"value": str(channel.id)}},
            upsert=True
        )
        await interaction.response.send_message(f"✅ Audit log channel set to {channel.mention}")

    @app_commands.command(name="auditlog", description="View recent audit log entries.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(limit="Number of entries to show (1-50)")
    async def view_audit_log(self, interaction: discord.Interaction, limit: int = 10):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database connection unavailable.", ephemeral=True)
        entries = await db_cog.audit_log.find({"guild_id": str(interaction.guild.id)}).sort("timestamp", -1).limit(min(limit, 50)).to_list(None)
        if not entries:
            return await interaction.followup.send("No audit log entries found.", ephemeral=True)
        embed = discord.Embed(title="📋 Audit Log", color=discord.Color.blue())
        for e in entries:
            embed.add_field(
                name=f"{e['action']} - {e['timestamp'].strftime('%Y-%m-%d %H:%M')}",
                value=f"Actor: {e['actor_name']}\nTarget: {e.get('target_name', 'N/A')}",
                inline=False
            )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AuditCog(bot))
