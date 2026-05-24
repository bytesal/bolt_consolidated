import discord
from discord import app_commands
from discord.ext import commands
import uuid
import datetime


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # Internal permission check
    # ------------------------------------------------------------------

    def has_mod_clearance(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in self.bot.DEVELOPER_IDS:
            return True
        return interaction.user.guild_permissions.moderate_members

    # ------------------------------------------------------------------
    # /warn
    # ------------------------------------------------------------------

    @app_commands.command(
        name="warn",
        description="Issue a formal warning to a server member.",
    )
    @app_commands.describe(
        target="The member to warn.",
        reason="The reason for the warning.",
        evidence="Optional URL linking to evidence (screenshot, etc.).",
    )
    async def warn(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        reason: str,
        evidence: str = None,
    ):
        if not self.has_mod_clearance(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission to issue warnings.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database connection unavailable.")

        case_id = str(uuid.uuid4())[:8].upper()

        await db_cog.mod_cases.insert_one(
            {
                "case_id":     case_id,
                "action":      "warn",
                "target_id":   str(target.id),
                "target_name": target.name,
                "issuer_id":   str(interaction.user.id),
                "issuer_name": interaction.user.name,
                "reason":      reason,
                "evidence":    evidence,
                "timestamp":   datetime.datetime.utcnow(),
            }
        )
        await db_cog.mod_users.update_one(
            {"_id": str(target.id)},
            {"$inc": {"warnings": 1}},
            upsert=True,
        )

        # Log quota activity for the issuing moderator
        quota_cog = self.bot.get_cog("StaffQuotaCog")
        if quota_cog and hasattr(quota_cog, "log_quota_activity"):
            await quota_cog.log_quota_activity(interaction.user.id, "weekly_mod_actions")

        # Notify the warned member via DM
        try:
            embed = discord.Embed(
                title="⚠️ Warning Issued",
                color=discord.Color.yellow(),
            )
            embed.add_field(name="Server", value=interaction.guild.name, inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Case ID", value=f"`#{case_id}`", inline=True)
            if evidence:
                embed.add_field(name="Evidence", value=evidence, inline=False)
            await target.send(embed=embed)
        except Exception:
            pass  # DMs may be disabled — non-critical

        await interaction.followup.send(
            f"✅ Warning issued to **{target.name}** — Case `#{case_id}`"
        )

    # ------------------------------------------------------------------
    # /adwarn
    # ------------------------------------------------------------------

    @app_commands.command(
        name="adwarn",
        description="Issue an advertising policy warning to a server member.",
    )
    @app_commands.describe(
        target="The member to warn.",
        reason="The reason for the advertising warning.",
        evidence="Optional URL linking to evidence.",
    )
    async def adwarn(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        reason: str,
        evidence: str = None,
    ):
        if not self.has_mod_clearance(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission to issue warnings.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database connection unavailable.")

        case_id = str(uuid.uuid4())[:8].upper()

        await db_cog.mod_cases.insert_one(
            {
                "case_id":     case_id,
                "action":      "adwarn",
                "target_id":   str(target.id),
                "target_name": target.name,
                "issuer_id":   str(interaction.user.id),
                "issuer_name": interaction.user.name,
                "reason":      reason,
                "evidence":    evidence,
                "timestamp":   datetime.datetime.utcnow(),
            }
        )
        await db_cog.mod_users.update_one(
            {"_id": str(target.id)},
            {"$inc": {"adwarnings": 1}},
            upsert=True,
        )

        # Log quota activity
        quota_cog = self.bot.get_cog("StaffQuotaCog")
        if quota_cog and hasattr(quota_cog, "log_quota_activity"):
            await quota_cog.log_quota_activity(
                interaction.user.id, "weekly_adwarns_executed"
            )

        # Notify the warned member via DM
        try:
            embed = discord.Embed(
                title="🚫 Advertising Policy Warning",
                color=discord.Color.orange(),
            )
            embed.add_field(name="Server", value=interaction.guild.name, inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Case ID", value=f"`#{case_id}`", inline=True)
            if evidence:
                embed.add_field(name="Evidence", value=evidence, inline=False)
            await target.send(embed=embed)
        except Exception:
            pass

        await interaction.followup.send(
            f"✅ Advertising warning issued to **{target.name}** — Case `#{case_id}`"
        )

    # ------------------------------------------------------------------
    # /history
    # ------------------------------------------------------------------

    @app_commands.command(
        name="history",
        description="View the moderation history of a user.",
    )
    @app_commands.describe(target="The user whose history you want to view.")
    async def history(self, interaction: discord.Interaction, target: discord.User):
        if not self.has_mod_clearance(interaction):
            return await interaction.response.send_message(
                "❌ You do not have permission to view moderation history.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database connection unavailable.")

        profile = (
            await db_cog.mod_users.find_one({"_id": str(target.id)})
            or {"warnings": 0, "adwarnings": 0}
        )
        cases = (
            await db_cog.mod_cases.find({"target_id": str(target.id)})
            .sort("timestamp", -1)
            .limit(5)
            .to_list(None)
        )

        embed = discord.Embed(
            title=f"Moderation History — {target.name}",
            color=discord.Color.blue(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(
            name="Warnings", value=str(profile.get("warnings", 0)), inline=True
        )
        embed.add_field(
            name="Ad Warnings",
            value=str(profile.get("adwarnings", 0)),
            inline=True,
        )

        for case in cases:
            embed.add_field(
                name=f"`#{case['case_id']}` — {case['action'].upper()}",
                value=f"By: {case['issuer_name']} | Reason: {case['reason']}",
                inline=False,
            )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
