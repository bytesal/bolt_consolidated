```python id="crossserver_moderation_complete"
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import uuid

from utils.checks import staff_or_developer


WARNING_THRESHOLDS = {
    3: ("timeout", 60 * 60),
    5: ("mute", 60 * 60 * 24),
    7: ("ban", None),
}


class ModerationCog(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.temp_punishment_loop.start()

    def cog_unload(self):

        self.temp_punishment_loop.cancel()

    # =========================================================
    # UTILITIES
    # =========================================================

    async def get_linked_servers(
        self,
        guild_id: int
    ):

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        if not db_cog:
            return None, None

        # =====================================================
        # Staff Server Lookup
        # =====================================================

        data = await db_cog.get_server_link(
            guild_id
        )

        if data:

            staff_guild = self.bot.get_guild(
                int(data["staff_guild_id"])
            )

            public_guild = self.bot.get_guild(
                int(data["public_guild_id"])
            )

            return (
                staff_guild,
                public_guild
            )

        # =====================================================
        # Public Server Lookup
        # =====================================================

        data = await db_cog.get_link_by_public(
            guild_id
        )

        if data:

            staff_guild = self.bot.get_guild(
                int(data["staff_guild_id"])
            )

            public_guild = self.bot.get_guild(
                int(data["public_guild_id"])
            )

            return (
                staff_guild,
                public_guild
            )

        return None, None

    async def ensure_staff_server(
        self,
        interaction: discord.Interaction
    ):

        staff_guild, _ = await self.get_linked_servers(
            interaction.guild.id
        )

        if not staff_guild:
            return False

        return (
            interaction.guild.id
            == staff_guild.id
        )

    async def get_public_member(
        self,
        interaction: discord.Interaction,
        user_id: int
    ):

        _, public_guild = await self.get_linked_servers(
            interaction.guild.id
        )

        if not public_guild:
            return None

        return public_guild.get_member(
            user_id
        )

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

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        _, public_guild = await self.get_linked_servers(
            interaction.guild.id
        )

        case_id = await self.generate_case()

        await db_cog.mod_cases.insert_one({

            "case_id": case_id,

            "guild_id": str(public_guild.id),

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

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        staff_guild, _ = await self.get_linked_servers(
            interaction.guild.id
        )

        if not staff_guild:
            return

        config = await db_cog.settings.find_one({
            "_id": f"modlog_{staff_guild.id}"
        })

        if not config:
            return

        channel = staff_guild.get_channel(
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

            await target.guild.ban(
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

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

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
        target: discord.User,
        reason: str,
        evidence: str = None
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        if not await self.ensure_staff_server(
            interaction
        ):

            return await interaction.followup.send(

                "❌ This command can only be used "
                "inside the linked staff server.",

                ephemeral=True
            )

        target = await self.get_public_member(
            interaction,
            target.id
        )

        if not target:

            return await interaction.followup.send(

                "❌ User not found in linked public server.",

                ephemeral=True
            )

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        await db_cog.mod_users.update_one(

            {"_id": str(target.id)},

            {"$inc": {"warnings": 1}},

            upsert=True
        )

        profile = await db_cog.mod_users.find_one({
            "_id": str(target.id)
        })

        warnings = profile.get(
            "warnings",
            0
        )

        case_id = await self.create_case(
            interaction,
            "warn",
            target,
            reason,
            evidence
        )

        _, public_guild = await self.get_linked_servers(
            interaction.guild.id
        )

        await self.send_dm(
            target,
            public_guild,
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
        target: discord.User,
        minutes: int,
        reason: str,
        evidence: str = None
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        if not await self.ensure_staff_server(
            interaction
        ):

            return await interaction.followup.send(
                "❌ Staff server only.",
                ephemeral=True
            )

        target = await self.get_public_member(
            interaction,
            target.id
        )

        if not target:

            return await interaction.followup.send(
                "❌ User not found.",
                ephemeral=True
            )

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

        _, public_guild = await self.get_linked_servers(
            interaction.guild.id
        )

        await self.send_dm(
            target,
            public_guild,
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

        await interaction.followup.send(
            f"✅ {target.mention} timed out."
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
        target: discord.User,
        reason: str,
        evidence: str = None
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        if not await self.ensure_staff_server(
            interaction
        ):

            return await interaction.followup.send(
                "❌ Staff server only.",
                ephemeral=True
            )

        target = await self.get_public_member(
            interaction,
            target.id
        )

        if not target:

            return await interaction.followup.send(
                "❌ User not found.",
                ephemeral=True
            )

        case_id = await self.create_case(
            interaction,
            "ban",
            target,
            reason,
            evidence
        )

        _, public_guild = await self.get_linked_servers(
            interaction.guild.id
        )

        await self.send_dm(
            target,
            public_guild,
            "Ban",
            reason,
            case_id,
            interaction.user,
            evidence
        )

        await public_guild.ban(
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

        await interaction.followup.send(
            f"✅ {target} banned successfully."
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
        target: discord.User,
        reason: str,
        evidence: str = None
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        if not await self.ensure_staff_server(
            interaction
        ):

            return await interaction.followup.send(
                "❌ Staff server only.",
                ephemeral=True
            )

        target = await self.get_public_member(
            interaction,
            target.id
        )

        if not target:

            return await interaction.followup.send(
                "❌ User not found.",
                ephemeral=True
            )

        case_id = await self.create_case(
            interaction,
            "kick",
            target,
            reason,
            evidence
        )

        _, public_guild = await self.get_linked_servers(
            interaction.guild.id
        )

        await self.send_dm(
            target,
            public_guild,
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

        await interaction.followup.send(
            f"✅ {target} kicked successfully."
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
```
