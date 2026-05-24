import os
import discord
from discord import app_commands
from discord.ext import commands
import uuid
import datetime

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def has_mod_clearance(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in self.bot.DEVELOPER_IDS:
            return True
        return interaction.user.guild_permissions.moderate_members

    @app_commands.command(name="warn", description="Issue a formal warning matrix entry.")
    @app_commands.describe(
        target="Target user mapping parameter footprint.",
        reason="Explicit descriptive violation rationale payload statement.",
        evidence="Optional string URL reference mapping to logged validation items."
    )
    async def warn(self, interaction: discord.Interaction, target: discord.Member, reason: str, evidence: str = None):
        if not self.has_mod_clearance(interaction):
            return await interaction.response.send_message("❌ Security Context Rejection: Insufficient operational verification clearance level.", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Core DB Connection Unavailable.", ephemeral=True)

        case_id = str(uuid.uuid4())[:8].upper()

        case_doc = {
            "case_id": case_id,
            "action": "warn",
            "target_id": str(target.id),
            "target_name": target.name,
            "issuer_id": str(interaction.user.id),
            "issuer_name": interaction.user.name,
            "reason": reason,
            "evidence": evidence,
            "timestamp": datetime.datetime.utcnow()
        }
        await db_cog.mod_cases.insert_one(case_doc)
        await db_cog.mod_users.update_one({"_id": str(target.id)}, {"$inc": {"warnings": 1}}, upsert=True)

        quota_cog = self.bot.get_cog("StaffQuotaCog")
        if quota_cog and hasattr(quota_cog, "log_quota_activity"):
            await quota_cog.log_quota_activity(interaction.user.id, "weekly_mod_actions")

        try:
            embed = discord.Embed(title="⚠️ Warning Matrix Issued", color=discord.Color.yellow())
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Case Hash Reference", value=case_id)
            await target.send(embed=embed)
        except Exception:
            pass

        await interaction.followup.send(f"✅ Warning archived cleanly as Case `#{case_id}`", ephemeral=True)

    @app_commands.command(name="adwarn", description="Issue warning specifically dealing with promotion protocol violations.")
    @app_commands.describe(
        target="Target user mapping parameter footprint.",
        reason="Explicit descriptive violation rationale payload statement.",
        evidence="Optional string URL reference mapping to logged validation items."
    )
    async def adwarn(self, interaction: discord.Interaction, target: discord.Member, reason: str, evidence: str = None):
        if not self.has_mod_clearance(interaction):
            return await interaction.response.send_message("❌ Security Context Rejection.", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Core DB Connection Unavailable.", ephemeral=True)

        case_id = str(uuid.uuid4())[:8].upper()

        case_doc = {
            "case_id": case_id,
            "action": "adwarn",
            "target_id": str(target.id),
            "target_name": target.name,
            "issuer_id": str(interaction.user.id),
            "issuer_name": interaction.user.name,
            "reason": reason,
            "evidence": evidence,
            "timestamp": datetime.datetime.utcnow()
        }
        await db_cog.mod_cases.insert_one(case_doc)
        await db_cog.mod_users.update_one({"_id": str(target.id)}, {"$inc": {"adwarnings": 1}}, upsert=True)

        quota_cog = self.bot.get_cog("StaffQuotaCog")
        if quota_cog and hasattr(quota_cog, "log_quota_activity"):
            await quota_cog.log_quota_activity(interaction.user.id, "weekly_adwarns_executed")

        try:
            embed = discord.Embed(title="🚫 Advertising Policy Infraction Logged", color=discord.Color.orange())
            embed.add_field(name="Case File ID", value=case_id)
            await target.send(embed=embed)
        except Exception:
            pass

        await interaction.followup.send(f"✅ Advertising infraction logged as Case `#{case_id}`", ephemeral=True)

    @app_commands.command(name="history", description="Query log tracking database for historic records regarding specific targets.")
    @app_commands.describe(target="Target profile configuration metadata identity search parameter.")
    async def history(self, interaction: discord.Interaction, target: discord.User):
        if not self.has_mod_clearance(interaction):
            return await interaction.response.send_message("❌ Security Access Restriction.", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Core DB Connection Unavailable.", ephemeral=True)
            
        profile = await db_cog.mod_users.find_one({"_id": str(target.id)}) or {"warnings": 0, "adwarnings": 0}
        cases = await db_cog.mod_cases.find({"target_id": str(target.id)}).sort("timestamp", -1).limit(5).to_list(None)

        embed = discord.Embed(title=f"Mod Profile Search: {target.name}", color=discord.Color.blue())
        embed.add_field(name="Standard Warnings", value=str(profile.get("warnings", 0)), inline=True)
        embed.add_field(name="Advertising System Violations", value=str(profile.get("adwarnings", 0)), inline=True)
        
        for c in cases:
            embed.add_field(name=f"`#{c['case_id']}` - {c['action'].upper()}", value=f"By: {c['issuer_name']} | Reason: {c['reason']}", inline=False)
            
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
