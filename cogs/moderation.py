import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import uuid

from utils.checks import staff_or_developer


# Warning escalation thresholds (based on ACTIVE warns)
WARNING_THRESHOLDS = {
    3: ("timeout", 60 * 60),      # 1 hour timeout
    5: ("mute", 60 * 60 * 24),    # 24h timeout (Discord calls it timeout)
    7: ("ban", None),
}


class ModerationCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.temp_punishment_loop.start()

    def cog_unload(self):
        self.temp_punishment_loop.cancel()

    # ------------------------------------------------------------
    # Helper: get linked servers (staff & public)
    # ------------------------------------------------------------
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

    async def generate_case(self) -> str:
        return str(uuid.uuid4())[:8].upper()

    async def create_case(self, interaction, action, target, reason, evidence=None, duration=None):
        db_cog = self.bot.get_cog("DatabaseCog")
        _, public_guild = await self.get_linked_servers(interaction.guild.id)

        case_id = await self.generate_case()
        await db_cog.mod_cases.insert_one({
            "case_id": case_id,
            "guild_id": str(public_guild.id) if public_guild else None,
            "action": action,
            "target_id": str(target.id),
            "target_name": target.name,
            "issuer_id": str(interaction.user.id),
            "issuer_name": interaction.user.name,
            "reason": reason,
            "evidence": evidence,
            "duration": duration,
            "timestamp": datetime.utcnow(),
            "active": True,
            "revoked": False   # for removed warns
        })

        await db_cog.mod_users.update_one(
            {"_id": str(target.id)},
            {"$inc": {"total_cases": 1}},
            upsert=True
        )
        return case_id

    async def send_dm(self, target, guild, action, reason, case_id, moderator,
                      evidence=None, warning_count=None, duration=None):
        try:
            embed = discord.Embed(
                title=f"Moderation Action • {action.upper()}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Server", value=guild.name, inline=False)
            embed.add_field(name="Moderator", value=moderator.name, inline=False)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Case ID", value=f"`#{case_id}`", inline=False)
            if duration:
                embed.add_field(name="Duration", value=duration, inline=False)
            if warning_count is not None:
                embed.add_field(name="Warning Count", value=str(warning_count), inline=False)
            if evidence:
                embed.add_field(name="Evidence", value=evidence, inline=False)
            await target.send(embed=embed)
        except Exception:
            pass

    async def log_action(self, interaction, action, target, reason, case_id, evidence=None, duration=None):
        db_cog = self.bot.get_cog("DatabaseCog")
        staff_guild, _ = await self.get_linked_servers(interaction.guild.id)
        if not staff_guild:
            return

        config = await db_cog.settings.find_one({"_id": f"modlog_{staff_guild.id}"})
        if not config:
            return

        channel = staff_guild.get_channel(int(config["value"]))
        if not channel:
            return

        embed = discord.Embed(
            title=f"🛡️ Moderation Action • {action.upper()}",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="User", value=f"{target.mention} (`{target.id}`)", inline=False)
        embed.add_field(name="Moderator", value=f"{interaction.user.mention}", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Case ID", value=f"`#{case_id}`", inline=True)
        if duration:
            embed.add_field(name="Duration", value=duration, inline=True)
        if evidence:
            embed.add_field(name="Evidence", value=evidence, inline=False)
        await channel.send(embed=embed)

    # ------------------------------------------------------------
    # Helper: get active warning count (supports legacy)
    # ------------------------------------------------------------
    async def _get_active_warn_count(self, user_id: int) -> int:
        db_cog = self.bot.get_cog("DatabaseCog")
        profile = await db_cog.mod_users.find_one({"_id": str(user_id)})
        if not profile:
            return 0

        # New system: active_warns list
        if "active_warns" in profile:
            # Count only non‑revoked warn cases
            active = 0
            for case_id in profile["active_warns"]:
                case = await db_cog.mod_cases.find_one({"case_id": case_id, "revoked": {"$ne": True}})
                if case and case.get("action") == "warn":
                    active += 1
            return active

        # Legacy: simple integer counter
        return profile.get("warnings", 0)

    async def handle_warning_escalation(self, interaction, target):
        active_warns = await self._get_active_warn_count(target.id)
        if active_warns not in WARNING_THRESHOLDS:
            return

        punishment, duration = WARNING_THRESHOLDS[active_warns]
        reason = f"Automatic escalation after {active_warns} active warnings."

        if punishment == "timeout":
            until = datetime.utcnow() + timedelta(seconds=duration)
            await target.timeout(until, reason=reason)
        elif punishment == "ban":
            await target.guild.ban(target, reason=reason)

    # ------------------------------------------------------------
    # /setmodlog
    # ------------------------------------------------------------
    @app_commands.command(name="setmodlog", description="Set the moderation log channel.")
    @staff_or_developer(administrator=True)
    async def set_modlog(self, interaction: discord.Interaction, channel: discord.TextChannel):
        db_cog = self.bot.get_cog("DatabaseCog")
        await db_cog.settings.update_one(
            {"_id": f"modlog_{interaction.guild.id}"},
            {"$set": {"value": str(channel.id)}},
            upsert=True
        )
        await interaction.response.send_message(f"✅ Mod‑log channel set to {channel.mention}")

    # ------------------------------------------------------------
    # /warn
    # ------------------------------------------------------------
    @app_commands.command(name="warn", description="Warn a member.")
    @staff_or_developer(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, target: discord.User,
                   reason: str, evidence: str = None):
        await interaction.response.defer(ephemeral=True)

        if not await self.ensure_staff_server(interaction):
            return await interaction.followup.send("❌ This command can only be used inside the linked staff server.", ephemeral=True)

        target = await self.get_public_member(interaction, target.id)
        if not target:
            return await interaction.followup.send("❌ User not found in linked public server.", ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")
        case_id = await self.create_case(interaction, "warn", target, reason, evidence)

        # Update user profile: add to active_warns list
        await db_cog.mod_users.update_one(
            {"_id": str(target.id)},
            {"$push": {"active_warns": case_id}, "$inc": {"warnings": 1}},
            upsert=True
        )

        _, public_guild = await self.get_linked_servers(interaction.guild.id)
        active_count = await self._get_active_warn_count(target.id)
        await self.send_dm(target, public_guild, "Warn", reason, case_id,
                           interaction.user, evidence, active_count)
        await self.log_action(interaction, "warn", target, reason, case_id, evidence)
        await self.handle_warning_escalation(interaction, target)

        await interaction.followup.send(f"✅ {target.mention} warned successfully.\nCase: `#{case_id}`")

    # ------------------------------------------------------------
    # /removewarn
    # ------------------------------------------------------------
    @app_commands.command(name="removewarn", description="Remove a specific warning by its case ID.")
    @staff_or_developer(moderate_members=True)
    async def remove_warn(self, interaction: discord.Interaction, target: discord.User, case_id: str):
        await interaction.response.defer(ephemeral=True)

        if not await self.ensure_staff_server(interaction):
            return await interaction.followup.send("❌ Staff server only.", ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")

        # Find the warn case
        case = await db_cog.mod_cases.find_one({"case_id": case_id, "target_id": str(target.id), "action": "warn"})
        if not case:
            return await interaction.followup.send("❌ Warn case not found. Make sure the case ID is correct and belongs to this user.", ephemeral=True)

        if case.get("revoked", False):
            return await interaction.followup.send("❌ This warning has already been removed.", ephemeral=True)

        # Mark as revoked
        await db_cog.mod_cases.update_one({"_id": case["_id"]}, {"$set": {"revoked": True, "active": False}})

        # Remove from user's active_warns list
        await db_cog.mod_users.update_one(
            {"_id": str(target.id)},
            {"$pull": {"active_warns": case_id}, "$inc": {"warnings": -1}}
        )

        # Log the removal
        staff_guild, _ = await self.get_linked_servers(interaction.guild.id)
        if staff_guild:
            config = await db_cog.settings.find_one({"_id": f"modlog_{staff_guild.id}"})
            if config:
                channel = staff_guild.get_channel(int(config["value"]))
                if channel:
                    embed = discord.Embed(
                        title="⚠️ Warning Removed",
                        color=discord.Color.green(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="User", value=f"{target.mention} (`{target.id}`)", inline=False)
                    embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
                    embed.add_field(name="Original Warn Case", value=f"`#{case_id}`", inline=False)
                    embed.add_field(name="Original Reason", value=case["reason"], inline=False)
                    await channel.send(embed=embed)

        # Notify user (optional)
        try:
            await target.send(f"✅ Your warning `#{case_id}` has been removed by staff.")
        except Exception:
            pass

        await interaction.followup.send(f"✅ Warning `#{case_id}` removed for {target.mention}.")

    # ------------------------------------------------------------
    # /warns - list active warns with IDs
    # ------------------------------------------------------------
    @app_commands.command(name="warns", description="List active warnings for a user.")
    @staff_or_developer(moderate_members=True)
    async def list_warns(self, interaction: discord.Interaction, target: discord.User):
        await interaction.response.defer(ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")
        profile = await db_cog.mod_users.find_one({"_id": str(target.id)})
        if not profile or not profile.get("active_warns"):
            return await interaction.followup.send(f"📭 {target.mention} has no active warnings.", ephemeral=True)

        active_warns = []
        for case_id in profile["active_warns"]:
            case = await db_cog.mod_cases.find_one({"case_id": case_id, "revoked": {"$ne": True}})
            if case and case["action"] == "warn":
                active_warns.append(case)

        if not active_warns:
            return await interaction.followup.send(f"📭 {target.mention} has no active warnings.", ephemeral=True)

        embed = discord.Embed(title=f"Active Warnings for {target.display_name}", color=discord.Color.orange())
        for w in active_warns[:10]:  # limit to 10
            embed.add_field(
                name=f"Case #{w['case_id']}",
                value=f"Reason: {w['reason']}\nModerator: {w['issuer_name']}\nDate: {w['timestamp'].strftime('%Y-%m-%d')}",
                inline=False
            )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ------------------------------------------------------------
    # /timeout, /ban, /kick, /history, /purge, /purgeuser
    # (unchanged from original except using updated helpers)
    # ------------------------------------------------------------
    @app_commands.command(name="timeout", description="Timeout a member.")
    @staff_or_developer(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, target: discord.User,
                      minutes: int, reason: str, evidence: str = None):
        await interaction.response.defer(ephemeral=True)
        if not await self.ensure_staff_server(interaction):
            return await interaction.followup.send("❌ Staff server only.", ephemeral=True)
        target = await self.get_public_member(interaction, target.id)
        if not target:
            return await interaction.followup.send("❌ User not found.", ephemeral=True)
        until = datetime.utcnow() + timedelta(minutes=minutes)
        await target.timeout(until, reason=reason)
        case_id = await self.create_case(interaction, "timeout", target, reason, evidence, minutes * 60)
        _, public_guild = await self.get_linked_servers(interaction.guild.id)
        await self.send_dm(target, public_guild, "Timeout", reason, case_id,
                           interaction.user, evidence, None, f"{minutes} minutes")
        await self.log_action(interaction, "timeout", target, reason, case_id, evidence, f"{minutes} minutes")
        await interaction.followup.send(f"✅ {target.mention} timed out.")

    @app_commands.command(name="ban", description="Ban a member.")
    @staff_or_developer(ban_members=True)
    async def ban(self, interaction: discord.Interaction, target: discord.User,
                  reason: str, evidence: str = None):
        await interaction.response.defer(ephemeral=True)
        if not await self.ensure_staff_server(interaction):
            return await interaction.followup.send("❌ Staff server only.", ephemeral=True)
        target = await self.get_public_member(interaction, target.id)
        if not target:
            return await interaction.followup.send("❌ User not found.", ephemeral=True)
        case_id = await self.create_case(interaction, "ban", target, reason, evidence)
        _, public_guild = await self.get_linked_servers(interaction.guild.id)
        await self.send_dm(target, public_guild, "Ban", reason, case_id, interaction.user, evidence)
        await public_guild.ban(target, reason=reason)
        await self.log_action(interaction, "ban", target, reason, case_id, evidence)
        await interaction.followup.send(f"✅ {target} banned successfully.")

    @app_commands.command(name="kick", description="Kick a member.")
    @staff_or_developer(kick_members=True)
    async def kick(self, interaction: discord.Interaction, target: discord.User,
                   reason: str, evidence: str = None):
        await interaction.response.defer(ephemeral=True)
        if not await self.ensure_staff_server(interaction):
            return await interaction.followup.send("❌ Staff server only.", ephemeral=True)
        target = await self.get_public_member(interaction, target.id)
        if not target:
            return await interaction.followup.send("❌ User not found.", ephemeral=True)
        case_id = await self.create_case(interaction, "kick", target, reason, evidence)
        _, public_guild = await self.get_linked_servers(interaction.guild.id)
        await self.send_dm(target, public_guild, "Kick", reason, case_id, interaction.user, evidence)
        await target.kick(reason=reason)
        await self.log_action(interaction, "kick", target, reason, case_id, evidence)
        await interaction.followup.send(f"✅ {target} kicked successfully.")

    @app_commands.command(name="history", description="View moderation history (last 10 actions).")
    @staff_or_developer(moderate_members=True)
    async def history(self, interaction: discord.Interaction, target: discord.User):
        db_cog = self.bot.get_cog("DatabaseCog")
        cases = await db_cog.mod_cases.find({"target_id": str(target.id)}).sort("timestamp", -1).limit(10).to_list(None)
        if not cases:
            return await interaction.response.send_message("No moderation history found.")
        embed = discord.Embed(title=f"Moderation History • {target}", color=discord.Color.blurple())
        for case in cases:
            revoked = " (REVOKED)" if case.get("revoked") else ""
            embed.add_field(
                name=f"{case['action'].upper()} • #{case['case_id']}{revoked}",
                value=f"Reason: {case['reason']}",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="purge", description="Delete a specific amount of messages.")
    @staff_or_developer(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True)
        if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
            return await interaction.followup.send("❌ I do not have permission to manage messages.", ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        embed = discord.Embed(title="🧹 Messages Purged", description=f"Deleted `{len(deleted)}` messages.", color=discord.Color.orange(), timestamp=datetime.utcnow())
        embed.set_footer(text=f"Moderator • {interaction.user}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="purgeuser", description="Delete messages from a specific user ID.")
    @staff_or_developer(manage_messages=True)
    async def purge_user(self, interaction: discord.Interaction, user_id: str, amount: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True)
        if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
            return await interaction.followup.send("❌ I do not have permission to manage messages.", ephemeral=True)
        deleted = []
        async for message in interaction.channel.history(limit=500):
            if str(message.author.id) == user_id:
                await message.delete()
                deleted.append(message)
                if len(deleted) >= amount:
                    break
        embed = discord.Embed(title="🧹 User Messages Purged", color=discord.Color.orange(), timestamp=datetime.utcnow())
        embed.add_field(name="Target User ID", value=f"`{user_id}`", inline=False)
        embed.add_field(name="Deleted Messages", value=str(len(deleted)), inline=False)
        embed.set_footer(text=f"Moderator • {interaction.user}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ------------------------------------------------------------
    # Temp loop (placeholder)
    # ------------------------------------------------------------
    @tasks.loop(minutes=1)
    async def temp_punishment_loop(self):
        pass

    @temp_punishment_loop.before_loop
    async def before_temp_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
