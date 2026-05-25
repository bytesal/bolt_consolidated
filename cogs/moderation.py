import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import uuid
from utils.logger import get_logger
from utils.checks import staff_or_developer

logger = get_logger("moderation")

WARNING_THRESHOLDS = {
    3: ("timeout", 60 * 60),
    5: ("mute", 60 * 60 * 24),
    7: ("ban", None),
}


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_punishment_loop.start()
        self.expiry_check_loop.start()

    def cog_unload(self):
        self.temp_punishment_loop.cancel()
        self.expiry_check_loop.cancel()

    # ------------------------------------------------------------
    # Helper methods
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

    async def create_case(self, interaction, action, target, reason, evidence=None, duration=None, expires_at=None):
        db_cog = self.bot.get_cog("DatabaseCog")
        _, public_guild = await self.get_linked_servers(interaction.guild.id)
        case_id = await self.generate_case()
        doc = {
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
            "revoked": False,
            "notes": []
        }
        if action == "warn" and expires_at:
            doc["expires_at"] = expires_at
        await db_cog.mod_cases.insert_one(doc)
        await db_cog.mod_users.update_one(
            {"_id": str(target.id)},
            {"$inc": {"total_cases": 1}},
            upsert=True
        )
        # Audit log
        audit_cog = self.bot.get_cog("AuditCog")
        if audit_cog:
            await audit_cog.log_audit(
                guild_id=interaction.guild.id,
                action=action,
                actor_id=interaction.user.id,
                actor_name=interaction.user.name,
                target_id=target.id,
                target_name=target.name,
                details={"reason": reason, "case_id": case_id, "evidence": evidence},
                severity="warning" if action == "warn" else "info"
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
        except Exception as e:
            logger.warning(f"Failed to send DM to {target.id}: {e}")

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

    async def _get_active_warn_count(self, user_id: int) -> int:
        db_cog = self.bot.get_cog("DatabaseCog")
        profile = await db_cog.mod_users.find_one({"_id": str(user_id)})
        if not profile:
            return 0
        if "active_warns" in profile:
            active = 0
            for case_id in profile["active_warns"]:
                case = await db_cog.mod_cases.find_one({"case_id": case_id, "revoked": {"$ne": True}})
                if case and case.get("action") == "warn":
                    active += 1
            return active
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
        logger.info(f"Escalation for {target.id}: {punishment} after {active_warns} warns")

    # ------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------
    @app_commands.command(name="setmodlog", description="Set the moderation log channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_modlog(self, interaction: discord.Interaction, channel: discord.TextChannel):
        db_cog = self.bot.get_cog("DatabaseCog")
        await db_cog.settings.update_one(
            {"_id": f"modlog_{interaction.guild.id}"},
            {"$set": {"value": str(channel.id)}},
            upsert=True
        )
        await interaction.response.send_message(f"✅ Mod‑log channel set to {channel.mention}")

    @app_commands.command(name="warn", description="Warn a member.")
    @app_commands.checks.cooldown(1, 5)
    @staff_or_developer(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, target: discord.User,
                   reason: str, evidence: str = None):
        await interaction.response.defer(ephemeral=True)
        if not await self.ensure_staff_server(interaction):
            return await interaction.followup.send("❌ This command can only be used inside the linked staff server.", ephemeral=True)
        target_member = await self.get_public_member(interaction, target.id)
        if not target_member:
            return await interaction.followup.send("❌ User not found in linked public server.", ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")
        # Get expiry days from guild settings
        expiry_days = 30
        setting = await db_cog.settings.find_one({"_id": f"warnexpiry_{interaction.guild.id}"})
        if setting:
            expiry_days = setting.get("value", 30)
        expires_at = None
        if expiry_days > 0:
            expires_at = datetime.utcnow() + timedelta(days=expiry_days)

        case_id = await self.create_case(interaction, "warn", target_member, reason, evidence, expires_at=expires_at)

        await db_cog.mod_users.update_one(
            {"_id": str(target_member.id)},
            {"$push": {"active_warns": case_id}, "$inc": {"warnings": 1}},
            upsert=True
        )

        _, public_guild = await self.get_linked_servers(interaction.guild.id)
        active_count = await self._get_active_warn_count(target_member.id)
        await self.send_dm(target_member, public_guild, "Warn", reason, case_id,
                           interaction.user, evidence, active_count)
        await self.log_action(interaction, "warn", target_member, reason, case_id, evidence)
        await self.handle_warning_escalation(interaction, target_member)
        await interaction.followup.send(f"✅ {target_member.mention} warned successfully.\nCase: `#{case_id}`")
        logger.info(f"Warn issued by {interaction.user.id} to {target_member.id} | Case {case_id}")

    @app_commands.command(name="removewarn", description="Remove a specific warning by its case ID.")
    @app_commands.checks.cooldown(1, 5)
    @staff_or_developer(moderate_members=True)
    async def remove_warn(self, interaction: discord.Interaction, target: discord.User, case_id: str):
        await interaction.response.defer(ephemeral=True)
        if not await self.ensure_staff_server(interaction):
            return await interaction.followup.send("❌ Staff server only.", ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        case = await db_cog.mod_cases.find_one({"case_id": case_id, "target_id": str(target.id), "action": "warn"})
        if not case:
            return await interaction.followup.send("❌ Warn case not found.", ephemeral=True)
        if case.get("revoked", False):
            return await interaction.followup.send("❌ This warning has already been removed.", ephemeral=True)

        await db_cog.mod_cases.update_one({"_id": case["_id"]}, {"$set": {"revoked": True, "active": False}})
        await db_cog.mod_users.update_one(
            {"_id": str(target.id)},
            {"$pull": {"active_warns": case_id}, "$inc": {"warnings": -1}}
        )

        # Log to audit
        audit_cog = self.bot.get_cog("AuditCog")
        if audit_cog:
            await audit_cog.log_audit(
                guild_id=interaction.guild.id,
                action="removewarn",
                actor_id=interaction.user.id,
                actor_name=interaction.user.name,
                target_id=target.id,
                target_name=target.name,
                details={"case_id": case_id, "original_reason": case["reason"]},
                severity="info"
            )

        staff_guild, _ = await self.get_linked_servers(interaction.guild.id)
        if staff_guild:
            config = await db_cog.settings.find_one({"_id": f"modlog_{staff_guild.id}"})
            if config:
                channel = staff_guild.get_channel(int(config["value"]))
                if channel:
                    embed = discord.Embed(title="⚠️ Warning Removed", color=discord.Color.green(), timestamp=datetime.utcnow())
                    embed.add_field(name="User", value=f"{target.mention} (`{target.id}`)", inline=False)
                    embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
                    embed.add_field(name="Original Warn Case", value=f"`#{case_id}`", inline=False)
                    embed.add_field(name="Original Reason", value=case["reason"], inline=False)
                    await channel.send(embed=embed)

        try:
            await target.send(f"✅ Your warning `#{case_id}` has been removed by staff.")
        except Exception:
            pass
        await interaction.followup.send(f"✅ Warning `#{case_id}` removed for {target.mention}.")
        logger.info(f"Warning {case_id} removed by {interaction.user.id}")

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
        for w in active_warns[:10]:
            embed.add_field(
                name=f"Case #{w['case_id']}",
                value=f"Reason: {w['reason']}\nModerator: {w['issuer_name']}\nDate: {w['timestamp'].strftime('%Y-%m-%d')}",
                inline=False
            )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="setwarnexpiry", description="Set number of days until warnings expire (0 = never).")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_warn_expiry(self, interaction: discord.Interaction, days: int):
        if days < 0:
            return await interaction.response.send_message("Days cannot be negative.", ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        await db_cog.settings.update_one(
            {"_id": f"warnexpiry_{interaction.guild.id}"},
            {"$set": {"value": days}},
            upsert=True
        )
        await interaction.response.send_message(f"✅ Warnings will expire after {days} days." if days > 0 else "✅ Warnings will never expire.")
        logger.info(f"Warning expiry set to {days} days by {interaction.user.id} in guild {interaction.guild.id}")

    @app_commands.command(name="casenote", description="Add a private note to a moderation case.")
    @app_commands.checks.cooldown(1, 3)
    @staff_or_developer(moderate_members=True)
    async def case_note(self, interaction: discord.Interaction, case_id: str, note: str):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        case = await db_cog.mod_cases.find_one({"case_id": case_id})
        if not case:
            return await interaction.followup.send("❌ Case not found.", ephemeral=True)
        note_doc = {
            "content": note,
            "author_id": str(interaction.user.id),
            "author_name": interaction.user.name,
            "timestamp": datetime.utcnow()
        }
        await db_cog.mod_cases.update_one(
            {"_id": case["_id"]},
            {"$push": {"notes": note_doc}}
        )
        # Audit log
        audit_cog = self.bot.get_cog("AuditCog")
        if audit_cog:
            await audit_cog.log_audit(
                guild_id=interaction.guild.id,
                action="casenote",
                actor_id=interaction.user.id,
                actor_name=interaction.user.name,
                target_id=None,
                target_name=None,
                details={"case_id": case_id, "note": note[:100]},
                severity="info"
            )
        await interaction.followup.send(f"✅ Note added to case `#{case_id}`.", ephemeral=True)
        logger.info(f"Note added to case {case_id} by {interaction.user.id}")

    @app_commands.command(name="caseview", description="View a moderation case with all notes.")
    @staff_or_developer(moderate_members=True)
    async def case_view(self, interaction: discord.Interaction, case_id: str):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        case = await db_cog.mod_cases.find_one({"case_id": case_id})
        if not case:
            return await interaction.followup.send("❌ Case not found.", ephemeral=True)
        embed = discord.Embed(title=f"Case #{case_id}", color=discord.Color.blurple(), timestamp=case["timestamp"])
        embed.add_field(name="Action", value=case["action"].upper(), inline=True)
        embed.add_field(name="User", value=f"{case['target_name']} (`{case['target_id']}`)", inline=True)
        embed.add_field(name="Moderator", value=case["issuer_name"], inline=True)
        embed.add_field(name="Reason", value=case["reason"], inline=False)
        if case.get("evidence"):
            embed.add_field(name="Evidence", value=case["evidence"], inline=False)
        if case.get("expires_at"):
            embed.add_field(name="Expires", value=case["expires_at"].strftime("%Y-%m-%d %H:%M UTC"), inline=False)
        if case.get("revoked"):
            embed.add_field(name="Status", value="REVOKED", inline=False)
        notes = case.get("notes", [])
        if notes:
            notes_text = ""
            for n in notes[-5:]:
                notes_text += f"**{n['author_name']}** ({n['timestamp'].strftime('%Y-%m-%d %H:%M')}): {n['content']}\n"
            embed.add_field(name="Notes (last 5)", value=notes_text or "None", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ------------------------------------------------------------
    # Existing moderation commands (with cooldowns)
    # ------------------------------------------------------------
    @app_commands.command(name="timeout", description="Timeout a member.")
    @app_commands.checks.cooldown(1, 5)
    @staff_or_developer(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, target: discord.User,
                      minutes: int, reason: str, evidence: str = None):
        await interaction.response.defer(ephemeral=True)
        if not await self.ensure_staff_server(interaction):
            return await interaction.followup.send("❌ Staff server only.", ephemeral=True)
        target_member = await self.get_public_member(interaction, target.id)
        if not target_member:
            return await interaction.followup.send("❌ User not found.", ephemeral=True)
        until = datetime.utcnow() + timedelta(minutes=minutes)
        await target_member.timeout(until, reason=reason)
        case_id = await self.create_case(interaction, "timeout", target_member, reason, evidence, minutes * 60)
        _, public_guild = await self.get_linked_servers(interaction.guild.id)
        await self.send_dm(target_member, public_guild, "Timeout", reason, case_id,
                           interaction.user, evidence, None, f"{minutes} minutes")
        await self.log_action(interaction, "timeout", target_member, reason, case_id, evidence, f"{minutes} minutes")
        await interaction.followup.send(f"✅ {target_member.mention} timed out.")
        logger.info(f"Timeout issued by {interaction.user.id} to {target_member.id} for {minutes} min")

    @app_commands.command(name="ban", description="Ban a member.")
    @app_commands.checks.cooldown(1, 5)
    @staff_or_developer(ban_members=True)
    async def ban(self, interaction: discord.Interaction, target: discord.User,
                  reason: str, evidence: str = None):
        await interaction.response.defer(ephemeral=True)
        if not await self.ensure_staff_server(interaction):
            return await interaction.followup.send("❌ Staff server only.", ephemeral=True)
        target_member = await self.get_public_member(interaction, target.id)
        if not target_member:
            return await interaction.followup.send("❌ User not found.", ephemeral=True)
        case_id = await self.create_case(interaction, "ban", target_member, reason, evidence)
        _, public_guild = await self.get_linked_servers(interaction.guild.id)
        await self.send_dm(target_member, public_guild, "Ban", reason, case_id, interaction.user, evidence)
        await public_guild.ban(target_member, reason=reason)
        await self.log_action(interaction, "ban", target_member, reason, case_id, evidence)
        await interaction.followup.send(f"✅ {target_member} banned successfully.")
        logger.info(f"Ban issued by {interaction.user.id} to {target_member.id}")

    @app_commands.command(name="kick", description="Kick a member.")
    @app_commands.checks.cooldown(1, 5)
    @staff_or_developer(kick_members=True)
    async def kick(self, interaction: discord.Interaction, target: discord.User,
                   reason: str, evidence: str = None):
        await interaction.response.defer(ephemeral=True)
        if not await self.ensure_staff_server(interaction):
            return await interaction.followup.send("❌ Staff server only.", ephemeral=True)
        target_member = await self.get_public_member(interaction, target.id)
        if not target_member:
            return await interaction.followup.send("❌ User not found.", ephemeral=True)
        case_id = await self.create_case(interaction, "kick", target_member, reason, evidence)
        _, public_guild = await self.get_linked_servers(interaction.guild.id)
        await self.send_dm(target_member, public_guild, "Kick", reason, case_id, interaction.user, evidence)
        await target_member.kick(reason=reason)
        await self.log_action(interaction, "kick", target_member, reason, case_id, evidence)
        await interaction.followup.send(f"✅ {target_member} kicked successfully.")
        logger.info(f"Kick issued by {interaction.user.id} to {target_member.id}")

    @app_commands.command(name="history", description="View moderation history (last 10 actions).")
    @staff_or_developer(moderate_members=True)
    async def history(self, interaction: discord.Interaction, target: discord.User):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        cases = await db_cog.mod_cases.find({"target_id": str(target.id)}).sort("timestamp", -1).limit(10).to_list(None)
        if not cases:
            return await interaction.followup.send("No moderation history found.")
        embed = discord.Embed(title=f"Moderation History • {target}", color=discord.Color.blurple())
        for case in cases:
            revoked = " (REVOKED)" if case.get("revoked") else ""
            embed.add_field(
                name=f"{case['action'].upper()} • #{case['case_id']}{revoked}",
                value=f"Reason: {case['reason']}",
                inline=False
            )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="purge", description="Delete a specific amount of messages.")
    @app_commands.checks.cooldown(1, 10)
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
    @app_commands.checks.cooldown(1, 10)
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
    # Background tasks
    # ------------------------------------------------------------
    @tasks.loop(minutes=1)
    async def temp_punishment_loop(self):
        # Placeholder – for future temp punishment checks
        pass

    @temp_punishment_loop.before_loop
    async def before_temp_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=1)
    async def expiry_check_loop(self):
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return
        now = datetime.utcnow()
        cursor = db_cog.mod_cases.find({
            "action": "warn",
            "revoked": False,
            "expires_at": {"$lt": now}
        })
        async for case in cursor:
            case_id = case["case_id"]
            target_id = case["target_id"]
            await db_cog.mod_cases.update_one(
                {"_id": case["_id"]},
                {"$set": {"revoked": True, "active": False, "expired": True}}
            )
            await db_cog.mod_users.update_one(
                {"_id": target_id},
                {"$pull": {"active_warns": case_id}, "$inc": {"warnings": -1}}
            )
            # Audit log for expiration
            audit_cog = self.bot.get_cog("AuditCog")
            if audit_cog:
                await audit_cog.log_audit(
                    guild_id=int(case.get("guild_id", 0)) if case.get("guild_id") else 0,
                    action="warning_expired",
                    actor_id=self.bot.user.id,
                    actor_name=self.bot.user.name,
                    target_id=int(target_id),
                    target_name=case.get("target_name", "Unknown"),
                    details={"case_id": case_id, "original_reason": case["reason"]},
                    severity="info"
                )
            logger.info(f"Warning {case_id} expired for user {target_id}")

    @expiry_check_loop.before_loop
    async def before_expiry_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
