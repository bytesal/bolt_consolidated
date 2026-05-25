import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import uuid

from utils.checks import staff_or_developer


class AdWarnCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_linked_servers(self, guild_id: int):
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return None, None
        data = await db_cog.get_server_link(guild_id)
        if data:
            staff_guild = self.bot.get_guild(int(data["staff_guild_id"]))
            public_guild = self.bot.get_guild(int(data["public_guild_id"]))
            return staff_guild, public_guild
        data = await db_cog.get_link_by_public(guild_id)
        if data:
            staff_guild = self.bot.get_guild(int(data["staff_guild_id"]))
            public_guild = self.bot.get_guild(int(data["public_guild_id"]))
            return staff_guild, public_guild
        return None, None

    async def ensure_staff_server(self, interaction: discord.Interaction) -> bool:
        staff_guild, _ = await self.get_linked_servers(interaction.guild.id)
        return staff_guild is not None and interaction.guild.id == staff_guild.id

    async def get_public_member(self, interaction: discord.Interaction, user_id: int):
        _, public_guild = await self.get_linked_servers(interaction.guild.id)
        if not public_guild:
            return None
        return public_guild.get_member(user_id)

    async def log_adwarn(self, interaction, target, reason, evidence):
        db_cog = self.bot.get_cog("DatabaseCog")
        staff_guild, public_guild = await self.get_linked_servers(interaction.guild.id)

        # Generate unique ID
        warn_id = str(uuid.uuid4())[:8].upper()

        # Store in ad_warns collection
        await db_cog.db["ad_warns"].insert_one({
            "warn_id": warn_id,
            "staff_guild_id": str(staff_guild.id) if staff_guild else None,
            "public_guild_id": str(public_guild.id) if public_guild else None,
            "target_id": str(target.id),
            "target_name": target.name,
            "issuer_id": str(interaction.user.id),
            "issuer_name": interaction.user.name,
            "reason": reason,
            "evidence": evidence,
            "timestamp": datetime.utcnow()
        })

        # Increment weekly quota counter for the staff member
        quota_cog = self.bot.get_cog("StaffQuotaCog")
        if quota_cog:
            await quota_cog.log_quota_activity(interaction.user.id, "weekly_adwarns_executed", 1)

        # Log to staff mod‑log channel
        if staff_guild:
            config = await db_cog.settings.find_one({"_id": f"modlog_{staff_guild.id}"})
            if config:
                channel = staff_guild.get_channel(int(config["value"]))
                if channel:
                    embed = discord.Embed(
                        title="⚠️ Ad‑Warn Issued",
                        color=discord.Color.dark_red(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="User", value=f"{target.mention} (`{target.id}`)", inline=False)
                    embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
                    embed.add_field(name="Reason", value=reason, inline=False)
                    if evidence:
                        embed.add_field(name="Evidence", value=evidence, inline=False)
                    embed.set_footer(text=f"Ad‑Warn ID: {warn_id}")
                    await channel.send(embed=embed)

        return warn_id

    # ------------------------------------------------------------
    # /adwarn
    # ------------------------------------------------------------
    @app_commands.command(name="adwarn", description="Issue an advertising warning (counts toward weekly quota).")
    @staff_or_developer(moderate_members=True)
    async def adwarn(self, interaction: discord.Interaction, target: discord.User,
                     reason: str, evidence: str = None):
        await interaction.response.defer(ephemeral=True)

        if not await self.ensure_staff_server(interaction):
            return await interaction.followup.send("❌ This command must be used in the staff server.", ephemeral=True)

        target_member = await self.get_public_member(interaction, target.id)
        if not target_member:
            return await interaction.followup.send("❌ User not found in the linked public server.", ephemeral=True)

        warn_id = await self.log_adwarn(interaction, target_member, reason, evidence)

        # Optional DM to user
        try:
            embed = discord.Embed(
                title="Advertising Warning",
                description=f"You have received an advertising warning in **{interaction.guild.name}**.",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            if evidence:
                embed.add_field(name="Evidence", value=evidence, inline=False)
            embed.add_field(name="Ad‑Warn ID", value=warn_id, inline=False)
            await target_member.send(embed=embed)
        except Exception:
            pass

        await interaction.followup.send(f"✅ Ad‑warn issued to {target_member.mention}. (ID: `{warn_id}`)")

    # ------------------------------------------------------------
    # /adwarnhistory
    # ------------------------------------------------------------
    @app_commands.command(name="adwarnhistory", description="View ad‑warn history for a user.")
    @staff_or_developer(moderate_members=True)
    async def adwarn_history(self, interaction: discord.Interaction, target: discord.User):
        await interaction.response.defer(ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")
        warns = await db_cog.db["ad_warns"].find({"target_id": str(target.id)}).sort("timestamp", -1).limit(10).to_list(None)

        if not warns:
            return await interaction.followup.send(f"📭 No ad‑warns found for {target.mention}.", ephemeral=True)

        embed = discord.Embed(title=f"Ad‑Warn History for {target.display_name}", color=discord.Color.red())
        for w in warns:
            embed.add_field(
                name=f"ID: {w['warn_id']}",
                value=f"Reason: {w['reason']}\nIssued by: {w['issuer_name']}\nDate: {w['timestamp'].strftime('%Y-%m-%d %H:%M')}",
                inline=False
            )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdWarnCog(bot))
