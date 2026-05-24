import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import uuid

from utils.checks import staff_or_developer


WARNING_THRESHOLDS = {
    3: ("timeout", 60 * 60),        # 1 hour
    5: ("mute", 60 * 60 * 24),      # 1 day
    7: ("ban", None),               # permanent
}


class ModerationCog(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.temp_punishment_loop.start()

    def cog_unload(self):

        self.temp_punishment_loop.cancel()

    # =========================================================
    # Permission Checks
    # =========================================================

    def has_mod_perms(
        self,
        interaction: discord.Interaction
    ):

        return (

            interaction.user.guild_permissions.moderate_members
            or interaction.user.guild_permissions.manage_messages
            or interaction.user.guild_permissions.ban_members
            or interaction.user.guild_permissions.kick_members
            or interaction.user.id in self.bot.DEVELOPER_IDS

        )

    # =========================================================
    # Utilities
    # =========================================================

    async def generate_case(self):

        return str(uuid.uuid4())[:8].upper()

    async def create_case(
        self,
        interaction,
        action,
        target,
        reason,
        evidence=None,
        duration=None,
    ):

        db_cog = self.bot.get_cog("DatabaseCog")

        case_id = await self.generate_case()

        await db_cog.mod_cases.insert_one({

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

            "active": True
        })

        await db_cog.mod_users.update_one(

            {"_id": str(target.id)},

            {
                "$inc": {
                    "total_cases": 1
                }
            },

            upsert=True
        )

        return case_id

    async def send_dm(
        self,
        target,
        guild,
        action,
        reason,
        case_id,
        moderator,
        evidence=None,
        warning_count=None,
        duration=None,
    ):

        try:

            embed = discord.Embed(
                title=f"Moderation Action • {action.upper()}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )

            embed.add_field(
                name="Server",
                value=guild.name,
                inline=False
            )

            embed.add_field(
                name="Moderator",
                value=moderator.name,
                inline=False
            )

            embed.add_field(
                name="Reason",
                value=reason,
                inline=False
            )

            embed.add_field(
                name="Case ID",
                value=f"`#{case_id}`",
                inline=False
            )

            if duration:

                embed.add_field(
                    name="Duration",
                    value=duration,
                    inline=False
                )

            if warning_count is not None:

                embed.add_field(
                    name="Warning Count",
                    value=str(warning_count),
                    inline=False
                )

            if evidence:

                embed.add_field(
                    name="Evidence",
                    value=evidence,
                    inline=False
                )

            await target.send(
                embed=embed
            )

        except Exception:
            pass

    async def log_action(
        self,
        interaction,
        action,
        target,
        reason,
        case_id,
        evidence=None,
        duration=None,
    ):

        db_cog = self.bot.get_cog("DatabaseCog")

        config = await db_cog.settings.find_one({
            "_id": f"modlog_{interaction.guild.id}"
        })

        if not config:
            return

        channel = interaction.guild.get_channel(
            int(config["value"])
        )

        if not channel:
            return

        embed = discord.Embed(
            title=f"🛡️ Moderation Action • {action.upper()}",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="User",
            value=f"{target.mention} (`{target.id}`)",
            inline=False
        )

        embed.add_field(
            name="Moderator",
            value=f"{interaction.user.mention}",
            inline=False
        )

        embed.add_field(
            name="Reason",
            value=reason,
            inline=False
        )

        embed.add_field(
            name="Case ID",
            value=f"`#{case_id}`",
            inline=True
        )

        if duration:

            embed.add_field(
                name="Duration",
                value=duration,
                inline=True
            )

        if evidence:

            embed.add_field(
                name="Evidence",
                value=evidence,
                inline=False
            )

        await channel.send(
            embed=embed
        )

    async def handle_warning_escalation(
        self,
        interaction,
        target,
        warnings
    ):

        if warnings not in WARNING_THRESHOLDS:
            return

        punishment, duration = WARNING_THRESHOLDS[warnings]

        reason = (
            f"Automatic escalation after "
            f"{warnings} warnings."
        )

        if punishment == "timeout":

            until = (
                datetime.utcnow()
                + timedelta(seconds=duration)
            )

            await target.timeout(
                until,
                reason=reason
            )

        elif punishment == "ban":

            await interaction.guild.ban(
                target,
                reason=reason
            )

    # =========================================================
    # CONFIG
    # =========================================================

    @app_commands.command(
        name="setmodlog",
        description="Set the moderation log channel."
    )

    @staff_or_developer(
        administrator=True
    )

    async def set_modlog(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):

        db_cog = self.bot.get_cog("DatabaseCog")

        await db_cog.settings.update_one(

            {"_id": f"modlog_{interaction.guild.id}"},

            {"$set": {"value": str(channel.id)}},

            upsert=True
        )

        await interaction.response.send_message(
            f"✅ Mod-log channel set to {channel.mention}"
        )

    # =========================================================
    # WARN
    # =========================================================

    @app_commands.command(
        name="warn",
        description="Warn a member."
    )

    @staff_or_developer(
        moderate_members=True
    )

    async def warn(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        reason: str,
        evidence: str = None
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        db_cog = self.bot.get_cog("DatabaseCog")

        await db_cog.mod_users.update_one(

            {"_id": str(target.id)},

            {"$inc": {"warnings": 1}},

            upsert=True
        )

        profile = await db_cog.mod_users.find_one({
            "_id": str(target.id)
        })

        warnings = profile.get("warnings", 0)

        case_id = await self.create_case(
            interaction,
            "warn",
            target,
            reason,
            evidence
        )

        await self.send_dm(
            target,
            interaction.guild,
            "Warn",
            reason,
            case_id,
            interaction.user,
            evidence,
            warnings
        )

        await self.log_action(
            interaction,
            "warn",
            target,
            reason,
            case_id,
            evidence
        )

        await self.handle_warning_escalation(
            interaction,
            target,
            warnings
        )

        await interaction.followup.send(
            f"✅ {target.mention} warned successfully.\n"
            f"Case: `#{case_id}`"
        )

    # =========================================================
    # TIMEOUT
    # =========================================================

    @app_commands.command(
        name="timeout",
        description="Timeout a member."
    )

    @staff_or_developer(
        moderate_members=True
    )

    async def timeout(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        minutes: int,
        reason: str,
        evidence: str = None
    ):

        until = (
            datetime.utcnow()
            + timedelta(minutes=minutes)
        )

        await target.timeout(
            until,
            reason=reason
        )

        case_id = await self.create_case(
            interaction,
            "timeout",
            target,
            reason,
            evidence,
            minutes * 60
        )

        await self.send_dm(
            target,
            interaction.guild,
            "Timeout",
            reason,
            case_id,
            interaction.user,
            evidence,
            None,
            f"{minutes} minutes"
        )

        await self.log_action(
            interaction,
            "timeout",
            target,
            reason,
            case_id,
            evidence,
            f"{minutes} minutes"
        )

        await interaction.response.send_message(
            f"✅ {target.mention} timed out "
            f"for {minutes} minutes."
        )

    # =========================================================
    # KICK
    # =========================================================

    @app_commands.command(
        name="kick",
        description="Kick a member."
    )

    @staff_or_developer(
        kick_members=True
    )

    async def kick(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        reason: str,
        evidence: str = None
    ):

        case_id = await self.create_case(
            interaction,
            "kick",
            target,
            reason,
            evidence
        )

        await self.send_dm(
            target,
            interaction.guild,
            "Kick",
            reason,
            case_id,
            interaction.user,
            evidence
        )

        await target.kick(
            reason=reason
        )

        await self.log_action(
            interaction,
            "kick",
            target,
            reason,
            case_id,
            evidence
        )

        await interaction.response.send_message(
            f"✅ {target} kicked successfully."
        )

    # =========================================================
    # BAN
    # =========================================================

    @app_commands.command(
        name="ban",
        description="Ban a member."
    )

    @staff_or_developer(
        ban_members=True
    )

    async def ban(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        reason: str,
        evidence: str = None
    ):

        case_id = await self.create_case(
            interaction,
            "ban",
            target,
            reason,
            evidence
        )

        await self.send_dm(
            target,
            interaction.guild,
            "Ban",
            reason,
            case_id,
            interaction.user,
            evidence
        )

        await interaction.guild.ban(
            target,
            reason=reason
        )

        await self.log_action(
            interaction,
            "ban",
            target,
            reason,
            case_id,
            evidence
        )

        await interaction.response.send_message(
            f"✅ {target} banned successfully."
        )

    # =========================================================
    # SOFTBAN
    # =========================================================

    @app_commands.command(
        name="softban",
        description="Softban a member."
    )

    @staff_or_developer(
        ban_members=True
    )

    async def softban(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        reason: str,
        evidence: str = None
    ):

        case_id = await self.create_case(
            interaction,
            "softban",
            target,
            reason,
            evidence
        )

        await self.send_dm(
            target,
            interaction.guild,
            "Softban",
            reason,
            case_id,
            interaction.user,
            evidence
        )

        await interaction.guild.ban(
            target,
            reason=reason,
            delete_message_days=1
        )

        await interaction.guild.unban(
            target
        )

        await self.log_action(
            interaction,
            "softban",
            target,
            reason,
            case_id,
            evidence
        )

        await interaction.response.send_message(
            f"✅ {target} softbanned successfully."
        )

    # =========================================================
    # PURGE
    # =========================================================

    @app_commands.command(
        name="purge",
        description="Delete messages."
    )

    @staff_or_developer(
        manage_messages=True
    )

    async def purge(
        self,
        interaction: discord.Interaction,
        amount: int
    ):

        deleted = await interaction.channel.purge(
            limit=amount
        )

        await interaction.response.send_message(
            f"✅ Deleted {len(deleted)} messages.",
            ephemeral=True
        )

    # =========================================================
    # LOCK
    # =========================================================

    @app_commands.command(
        name="lock",
        description="Lock the channel."
    )

    @staff_or_developer(
        manage_channels=True
    )

    async def lock(
        self,
        interaction: discord.Interaction
    ):

        overwrite = interaction.channel.overwrites_for(
            interaction.guild.default_role
        )

        overwrite.send_messages = False

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite
        )

        await interaction.response.send_message(
            "🔒 Channel locked."
        )

    # =========================================================
    # UNLOCK
    # =========================================================

    @app_commands.command(
        name="unlock",
        description="Unlock the channel."
    )

    @staff_or_developer(
        manage_channels=True
    )

    async def unlock(
        self,
        interaction: discord.Interaction
    ):

        overwrite = interaction.channel.overwrites_for(
            interaction.guild.default_role
        )

        overwrite.send_messages = True

        await interaction.channel.set_permissions(
            interaction.guild.default_role,
            overwrite=overwrite
        )

        await interaction.response.send_message(
            "🔓 Channel unlocked."
        )

    # =========================================================
    # SLOWMODE
    # =========================================================

    @app_commands.command(
        name="slowmode",
        description="Set slowmode."
    )

    @staff_or_developer(
        manage_channels=True
    )

    async def slowmode(
        self,
        interaction: discord.Interaction,
        seconds: int
    ):

        await interaction.channel.edit(
            slowmode_delay=seconds
        )

        await interaction.response.send_message(
            f"🐢 Slowmode set to "
            f"{seconds} seconds."
        )

    # =========================================================
    # HISTORY
    # =========================================================

    @app_commands.command(
        name="history",
        description="View moderation history."
    )

    @staff_or_developer(
        moderate_members=True
    )

    async def history(
        self,
        interaction: discord.Interaction,
        target: discord.User
    ):

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        cases = await db_cog.mod_cases.find({

            "target_id": str(target.id)

        }).sort(

            "timestamp",
            -1

        ).limit(10).to_list(None)

        if not cases:

            return await interaction.response.send_message(
                "No moderation history found."
            )

        embed = discord.Embed(
            title=f"Moderation History • {target}",
            color=discord.Color.blurple()
        )

        for case in cases:

            embed.add_field(

                name=(
                    f"{case['action'].upper()} "
                    f"• #{case['case_id']}"
                ),

                value=f"Reason: {case['reason']}",

                inline=False
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # =========================================================
    # TEMP LOOP
    # =========================================================

    @tasks.loop(minutes=1)
    async def temp_punishment_loop(self):
        pass

    @temp_punishment_loop.before_loop
    async def before_temp_loop(self):

        await self.bot.wait_until_ready()


async def setup(bot):

    await bot.add_cog(
        ModerationCog(bot)
    )
