import discord
from discord import app_commands
from discord.ext import commands
import traceback
import io
import contextlib
from datetime import datetime


class DeveloperCog(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # =====================================================
    # CHECKS
    # =====================================================

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ):

        return (
            interaction.user.id
            in self.bot.DEVELOPER_IDS
        )

    # =====================================================
    # /SYNC
    # =====================================================

    @app_commands.command(
        name="sync",
        description="Sync all slash commands."
    )
    async def sync(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        synced = await self.bot.tree.sync()

        await interaction.followup.send(
            f"✅ Synced {len(synced)} commands."
        )

    # =====================================================
    # /LOAD
    # =====================================================

    @app_commands.command(
        name="load",
        description="Load a cog."
    )
    async def load(
        self,
        interaction: discord.Interaction,
        cog: str
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        try:

            await self.bot.load_extension(
                f"cogs.{cog}"
            )

            await interaction.followup.send(
                f"✅ Loaded cog: `{cog}`"
            )

        except Exception as e:

            await interaction.followup.send(
                f"❌ Failed loading `{cog}`\n```py\n{e}\n```"
            )

    # =====================================================
    # /RELOAD
    # =====================================================

    @app_commands.command(
        name="reload",
        description="Reload a cog."
    )
    async def reload(
        self,
        interaction: discord.Interaction,
        cog: str
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        try:

            await self.bot.reload_extension(
                f"cogs.{cog}"
            )

            await interaction.followup.send(
                f"✅ Reloaded cog: `{cog}`"
            )

        except Exception as e:

            await interaction.followup.send(
                f"❌ Failed reloading `{cog}`\n```py\n{e}\n```"
            )

    # =====================================================
    # /UNLOAD
    # =====================================================

    @app_commands.command(
        name="unload",
        description="Unload a cog."
    )
    async def unload(
        self,
        interaction: discord.Interaction,
        cog: str
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        try:

            await self.bot.unload_extension(
                f"cogs.{cog}"
            )

            await interaction.followup.send(
                f"✅ Unloaded cog: `{cog}`"
            )

        except Exception as e:

            await interaction.followup.send(
                f"❌ Failed unloading `{cog}`\n```py\n{e}\n```"
            )

    # =====================================================
    # /SHUTDOWN
    # =====================================================

    @app_commands.command(
        name="shutdown",
        description="Shutdown the bot."
    )
    async def shutdown(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.send_message(
            "🛑 Shutting down...",
            ephemeral=True
        )

        await self.bot.close()

    # =====================================================
    # /EVAL
    # =====================================================

    @app_commands.command(
        name="eval",
        description="Execute Python code."
    )
    async def eval(
        self,
        interaction: discord.Interaction,
        code: str
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        env = {

            "bot": self.bot,
            "discord": discord,
            "commands": commands,
            "interaction": interaction,
            "__import__": __import__,
        }

        stdout = io.StringIO()

        try:

            with contextlib.redirect_stdout(stdout):

                exec(
                    f"async def func():\n"
                    + "\n".join(
                        f"    {line}"
                        for line in code.split("\n")
                    ),
                    env
                )

                result = await env["func"]()

            output = stdout.getvalue()

            if result is not None:
                output += str(result)

            if not output:
                output = "✅ Code executed successfully."

            await interaction.followup.send(
                f"```py\n{output[:1900]}\n```"
            )

        except Exception:

            error = traceback.format_exc()

            await interaction.followup.send(
                f"```py\n{error[:1900]}\n```"
            )

    # =====================================================
    # /SETSTAFFSERVER
    # =====================================================

    @app_commands.command(
        name="setstaffserver",
        description="Set the global staff control server."
    )
    async def set_staff_server(
        self,
        interaction: discord.Interaction,
        guild_id: str
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        guild = self.bot.get_guild(
            int(guild_id)
        )

        if not guild:

            return await interaction.followup.send(
                "❌ Bot is not inside that server."
            )

        await db_cog.settings.update_one(

            {"_id": "staff_control_guild"},

            {
                "$set": {
                    "guild_id": guild_id,
                    "updated_at": datetime.utcnow()
                }
            },

            upsert=True
        )

        await interaction.followup.send(
            f"✅ Staff control server set to:\n"
            f"**{guild.name}** (`{guild.id}`)"
        )

    # =====================================================
    # /STAFFSERVER
    # =====================================================

    @app_commands.command(
        name="staffserver",
        description="View current staff control server."
    )
    async def staff_server(
        self,
        interaction: discord.Interaction
    ):

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        data = await db_cog.settings.find_one({
            "_id": "staff_control_guild"
        })

        if not data:

            return await interaction.response.send_message(
                "❌ No staff server configured.",
                ephemeral=True
            )

        guild = self.bot.get_guild(
            int(data["guild_id"])
        )

        if not guild:

            return await interaction.response.send_message(
                "❌ Configured staff server not found.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="👥 Staff Control Server",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Server",
            value=f"{guild.name}",
            inline=False
        )

        embed.add_field(
            name="Guild ID",
            value=f"`{guild.id}`",
            inline=False
        )

        embed.add_field(
            name="Members",
            value=str(guild.member_count),
            inline=False
        )

        if guild.icon:
            embed.set_thumbnail(
                url=guild.icon.url
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # =====================================================
    # /BLACKLIST
    # =====================================================

    @app_commands.command(
        name="blacklist",
        description="Blacklist a user globally."
    )
    async def blacklist(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        reason: str
    ):

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        await db_cog.blacklist.update_one(

            {"_id": str(user.id)},

            {
                "$set": {
                    "reason": reason,
                    "added_by": str(interaction.user.id),
                    "timestamp": datetime.utcnow()
                }
            },

            upsert=True
        )

        await interaction.response.send_message(
            f"🚫 {user} has been blacklisted.\n"
            f"Reason: {reason}",
            ephemeral=True
        )

    # =====================================================
    # /UNBLACKLIST
    # =====================================================

    @app_commands.command(
        name="unblacklist",
        description="Remove a user from blacklist."
    )
    async def unblacklist(
        self,
        interaction: discord.Interaction,
        user: discord.User
    ):

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        await db_cog.blacklist.delete_one({
            "_id": str(user.id)
        })

        await interaction.response.send_message(
            f"✅ Removed {user} from blacklist.",
            ephemeral=True
        )

    # =====================================================
    # /BOTSTATS
    # =====================================================

    @app_commands.command(
        name="botstats",
        description="View bot analytics."
    )
    async def botstats(
        self,
        interaction: discord.Interaction
    ):

        guilds = len(self.bot.guilds)

        users = sum(
            guild.member_count
            for guild in self.bot.guilds
        )

        embed = discord.Embed(
            title="📊 Bot Analytics",
            color=discord.Color.green()
        )

        embed.add_field(
            name="Servers",
            value=str(guilds),
            inline=True
        )

        embed.add_field(
            name="Users",
            value=str(users),
            inline=True
        )

        embed.add_field(
            name="Developers",
            value=str(len(self.bot.DEVELOPER_IDS)),
            inline=True
        )

        embed.set_footer(
            text=f"{self.bot.user.name}"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


async def setup(bot):

    await bot.add_cog(
        DeveloperCog(bot)
    )
