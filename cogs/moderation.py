import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import uuid
import traceback
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
    async def get_target_member(self, interaction: discord.Interaction, user_id: int):
        return interaction.guild.get_member(user_id)

    async def generate_case(self) -> str:
        return str(uuid.uuid4())[:8].upper()

    async def create_case(self, interaction, action, target, reason, evidence=None, duration=None, expires_at=None):
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            logger.error("DatabaseCog not available")
            return None
        case_id = await self.generate_case()
        doc = {
            "case_id": case_id,
            "guild_id": str(interaction.guild.id),
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
        try:
            await db_cog.mod_cases.insert_one(doc)
            await db_cog.mod_users.update_one(
                {"_id": str(target.id)},
                {"$inc": {"total_cases": 1}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to create case: {e}")
            logger.error(traceback.format_exc())
            return None
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
        if not db_cog:
            return
        config = await db_cog.settings.find_one({"_id": f"modlog_{interaction.guild.id}"})
        if not config:
            return
        channel = interaction.guild.get_channel(int(config["value"]))
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
        if not db_cog:
            return 0
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
    # Warn command with robust error handling
    # ------------------------------------------------------------
    @app_commands.command(name="warn", description="Warn a member.")
    @app_commands.checks.cooldown(1, 5)
    @staff_or_developer(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, target: discord.User,
                   reason: str, evidence: str = None):
        logger.info(f"=== /warn called by {interaction.user.id} in guild {interaction.guild.id} ===")
        
        # Safe defer - handle expired interactions
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
                logger.info("Deferred response")
            else:
                logger.warning("Interaction already responded, using followup")
        except discord.NotFound as e:
            logger.error(f"Interaction not found (likely expired): {e}")
            # Cannot respond, so just return
            return
        except Exception as e:
            logger.error(f"Failed to defer: {e}")
            try:
                await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)
            except:
                pass
            return

        try:
            target_member = interaction.guild.get_member(target.id)
            if not target_member:
                logger.warning(f"Target {target.id} not found in guild")
                await interaction.followup.send("❌ User not found in this server.", ephemeral=True)
                return
            logger.info(f"Target member found: {target_member.id}")

            db_cog = self.bot.get_cog("DatabaseCog")
            if not db_cog:
                logger.error("DatabaseCog not available")
                await interaction.followup.send("❌ Database not available.", ephemeral=True)
                return
            logger.info("DatabaseCog retrieved")

            expiry_days = 30
            setting = await db_cog.settings.find_one({"_id": f"warnexpiry_{interaction.guild.id}"})
            if setting:
                expiry_days = setting.get("value", 30)
            expires_at = None
            if expiry_days > 0:
                expires_at = datetime.utcnow() + timedelta(days=expiry_days)
            logger.info(f"Expiry set to {expiry_days} days")

            case_id = await self.create_case(interaction, "warn", target_member, reason, evidence, expires_at=expires_at)
            if not case_id:
                logger.error("Failed to create case")
                await interaction.followup.send("❌ Failed to create case. Check database connection.", ephemeral=True)
                return
            logger.info(f"Case created: {case_id}")

            await db_cog.mod_users.update_one(
                {"_id": str(target_member.id)},
                {"$push": {"active_warns": case_id}, "$inc": {"warnings": 1}},
                upsert=True
            )
            logger.info("User profile updated")

            active_count = await self._get_active_warn_count(target_member.id)
            await self.send_dm(target_member, interaction.guild, "Warn", reason, case_id,
                               interaction.user, evidence, active_count)
            logger.info("DM sent")

            await self.log_action(interaction, "warn", target_member, reason, case_id, evidence)
            logger.info("Action logged")

            await self.handle_warning_escalation(interaction, target_member)
            logger.info("Escalation check completed")

            await interaction.followup.send(f"✅ {target_member.mention} warned successfully.\nCase: `#{case_id}`")
            logger.info(f"=== /warn completed successfully ===")

        except discord.NotFound as e:
            logger.error(f"Interaction expired during command execution: {e}")
            # Cannot respond, but we already logged
        except Exception as e:
            logger.error(f"Unhandled exception in /warn: {e}")
            logger.error(traceback.format_exc())
            try:
                await interaction.followup.send("❌ An internal error occurred. Check logs.", ephemeral=True)
            except:
                pass

    # ------------------------------------------------------------
    # Other commands (same robust pattern can be applied, but keep as before)
    # ------------------------------------------------------------
    @app_commands.command(name="setmodlog", description="Set the moderation log channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_modlog(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database error.", ephemeral=True)
        await db_cog.settings.update_one(
            {"_id": f"modlog_{interaction.guild.id}"},
            {"$set": {"value": str(channel.id)}},
            upsert=True
        )
        await interaction.followup.send(f"✅ Mod‑log channel set to {channel.mention}")

    @app_commands.command(name="removewarn", description="Remove a specific warning by its case ID.")
    @app_commands.checks.cooldown(1, 5)
    @staff_or_developer(moderate_members=True)
    async def remove_warn(self, interaction: discord.Interaction, target: discord.User, case_id: str):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database error.", ephemeral=True)
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
        config = await db_cog.settings.find_one({"_id": f"modlog_{interaction.guild.id}"})
        if config:
            channel = interaction.guild.get_channel(int(config["value"]))
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

    @app_commands.command(name="warns", description="List active warnings for a user.")
    @staff_or_developer(moderate_members=True)
    async def list_warns(self, interaction: discord.Interaction, target: discord.User):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database error.", ephemeral=True)
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
        await interaction.response.defer(ephemeral=True)
        if days < 0:
            return await interaction.followup.send("Days cannot be negative.", ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database error.", ephemeral=True)
        await db_cog.settings.update_one(
            {"_id": f"warnexpiry_{interaction.guild.id}"},
            {"$set": {"value": days}},
            upsert=True
        )
        await interaction.followup.send(f"✅ Warnings will expire after {days} days." if days > 0 else "✅ Warnings will never expire.")

    @app_commands.command(name="casenote", description="Add a private note to a moderation case.")
    @app_commands.checks.cooldown(1, 3)
    @staff_or_developer(moderate_members=True)
    async def case_note(self, interaction: discord.Interaction, case_id: str, note: str):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database error.", ephemeral=True)
        case = await db_cog.mod_cases.find_one({"case_id": case_id})
        if not case:
            return await interaction.followup.send("❌ Case not found.", ephemeral=True)
        note_doc = {
            "content": note,
            "author_id": str(interaction.user.id),
            "author_name": interaction.user.name,
            "timestamp": datetime.utcnow()
        }
        await db_cog.mod_cases.update_one({"_id": case["_id"]}, {"$push": {"notes": note_doc}})
        await interaction.followup.send(f"✅ Note added to case `#{case_id}`.", ephemeral=True)

    @app_commands.command(name="caseview", description="View a moderation case with all notes.")
    @staff_or_developer(moderate_members=True)
    async def case_view(self, interaction: discord.Interaction, case_id: str):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database error.", ephemeral=True)
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

    @app_commands.command(name="timeout", description="Timeout a member.")
    @app_commands.checks.cooldown(1, 5)
    @staff_or_developer(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, target: discord.User,
                      minutes: int, reason: str, evidence: str = None):
        await interaction.response.defer(ephemeral=True)
        target_member = interaction.guild.get_member(target.id)
        if not target_member:
            return await interaction.followup.send("❌ User not found.", ephemeral=True)
        until = datetime.utcnow() + timedelta(minutes=minutes)
        await target_member.timeout(until, reason=reason)
        case_id = await self.create_case(interaction, "timeout", target_member, reason, evidence, minutes * 60)
        await self.send_dm(target_member, interaction.guild, "Timeout", reason, case_id,
                           interaction.user, evidence, None, f"{minutes} minutes")
        await self.log_action(interaction, "timeout", target_member, reason, case_id, evidence, f"{minutes} minutes")
        await interaction.followup.send(f"✅ {target_member.mention} timed out.")

    @app_commands.command(name="ban", description="Ban a member.")
    @app_commands.checks.cooldown(1, 5)
    @staff_or_developer(ban_members=True)
    async def ban(self, interaction: discord.Interaction, target: discord.User,
                  reason: str, evidence: str = None):
        await interaction.response.defer(ephemeral=True)
        target_member = interaction.guild.get_member(target.id)
        if not target_member:
            return await interaction.followup.send("❌ User not found.", ephemeral=True)
        case_id = await self.create_case(interaction, "ban", target_member, reason, evidence)
        await self.send_dm(target_member, interaction.guild, "Ban", reason, case_id, interaction.user, evidence)
        await target_member.ban(reason=reason)
        await self.log_action(interaction, "ban", target_member, reason, case_id, evidence)
        await interaction.followup.send(f"✅ {target_member} banned successfully.")

    @app_commands.command(name="kick", description="Kick a member.")
    @app_commands.checks.cooldown(1, 5)
    @staff_or_developer(kick_members=True)
    async def kick(self, interaction: discord.Interaction, target: discord.User,
                   reason: str, evidence: str = None):
        await interaction.response.defer(ephemeral=True)
        target_member = interaction.guild.get_member(target.id)
        if not target_member:
            return await interaction.followup.send("❌ User not found.", ephemeral=True)
        case_id = await self.create_case(interaction, "kick", target_member, reason, evidence)
        await self.send_dm(target_member, interaction.guild, "Kick", reason, case_id, interaction.user, evidence)
        await target_member.kick(reason=reason)
        await self.log_action(interaction, "kick", target_member, reason, case_id, evidence)
        await interaction.followup.send(f"✅ {target_member} kicked successfully.")

    @app_commands.command(name="history", description="View moderation history (last 10 actions).")
    @staff_or_developer(moderate_members=True)
    async def history(self, interaction: discord.Interaction, target: discord.User):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database error.", ephemeral=True)
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
            logger.info(f"Warning {case_id} expired for user {target_id}")

    @expiry_check_loop.before_loop
    async def before_expiry_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))