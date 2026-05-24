import discord
from discord import app_commands
from discord.ext import commands


class CoreCog(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # =========================================================
    # UTILITIES
    # =========================================================

    def is_dev(self, user_id: int) -> bool:

        return user_id in self.bot.DEVELOPER_IDS

    async def clean_permission_check(
        self,
        interaction: discord.Interaction,
        perm: str = None
    ) -> bool:

        if self.is_dev(interaction.user.id):

            return True

        if (
            perm
            and hasattr(
                interaction.user.guild_permissions,
                perm
            )
        ):

            return getattr(
                interaction.user.guild_permissions,
                perm
            )

        return interaction.user.guild_permissions.administrator

    # =========================================================
    # /LINKSERVER
    # =========================================================

    @app_commands.command(
        name="linkserver",
        description="Link this staff server to a public server."
    )

    @app_commands.describe(
        public_guild_id="The public server ID."
    )

    async def link_server_command(
        self,
        interaction: discord.Interaction,
        public_guild_id: str
    ):

        if not await self.clean_permission_check(
            interaction
        ):

            return await interaction.response.send_message(

                "❌ Administrator permission or Developer identity required.",

                ephemeral=True
            )

        try:

            target_id = int(
                public_guild_id
            )

        except ValueError:

            return await interaction.response.send_message(

                "❌ Invalid server ID.",

                ephemeral=True
            )

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        if not db_cog:

            return await interaction.response.send_message(

                "❌ Database connection unavailable.",

                ephemeral=True
            )

        await db_cog.link_servers(
            interaction.guild.id,
            target_id
        )

        embed = discord.Embed(

            title="✅ Server Link Established",

            description=(

                f"This server has been configured "
                f"as the Staff Server.\n\n"

                f"Linked Public Server ID:\n"
                f"`{target_id}`"

            ),

            color=discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed
        )

    # =========================================================
    # /SETPREFIX
    # =========================================================

    @app_commands.command(
        name="setprefix",
        description="Change the bot prefix."
    )

    @app_commands.describe(
        prefix="New server prefix."
    )

    async def set_prefix_command(
        self,
        interaction: discord.Interaction,
        prefix: str
    ):

        if not await self.clean_permission_check(
            interaction
        ):

            return await interaction.response.send_message(

                "❌ Administrator permission required.",

                ephemeral=True
            )

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        if not db_cog:

            return await interaction.response.send_message(

                "❌ Database connection unavailable.",

                ephemeral=True
            )

        await db_cog.set_guild_prefix(
            interaction.guild.id,
            prefix
        )

        await interaction.response.send_message(

            f"✅ Prefix updated to `{prefix}`"

        )

    # =========================================================
    # /BOTSTATUS
    # =========================================================

    @app_commands.command(
        name="botstatus",
        description="Developer only command."
    )

    @app_commands.describe(
        status_type="online / idle / dnd / invisible",
        activity_text="Presence text."
    )

    async def bot_status_command(
        self,
        interaction: discord.Interaction,
        status_type: str,
        activity_text: str
    ):

        if not self.is_dev(
            interaction.user.id
        ):

            return await interaction.response.send_message(

                "❌ Developer only command.",

                ephemeral=True
            )

        status_map = {

            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible,
        }

        status = status_map.get(
            status_type.lower(),
            discord.Status.online
        )

        await self.bot.change_presence(

            status=status,

            activity=discord.Game(
                name=activity_text
            )
        )

        await interaction.response.send_message(

            "✅ Bot status updated.",

            ephemeral=True
        )

    # =========================================================
    # /SETBOTNAME
    # =========================================================

    @app_commands.command(
        name="setbotname",
        description="Rename the bot account."
    )

    @app_commands.describe(
        new_name="New bot username."
    )

    async def set_bot_name_command(
        self,
        interaction: discord.Interaction,
        new_name: str
    ):

        if not self.is_dev(
            interaction.user.id
        ):

            return await interaction.response.send_message(

                "❌ Developer only command.",

                ephemeral=True
            )

        try:

            await self.bot.user.edit(
                username=new_name
            )

            await interaction.response.send_message(

                f"✅ Bot username changed to:\n"
                f"**{new_name}**"

            )

        except Exception as e:

            await interaction.response.send_message(

                f"❌ Failed:\n`{e}`",

                ephemeral=True
            )

    # =========================================================
    # /SYNC
    # =========================================================

    @app_commands.command(
        name="sync",
        description="Sync slash commands instantly."
    )

    async def sync_command(
        self,
        interaction: discord.Interaction
    ):

        if not self.is_dev(
            interaction.user.id
        ):

            return await interaction.response.send_message(

                "❌ Developer only command.",

                ephemeral=True
            )

        await interaction.response.defer(
            ephemeral=True
        )

        try:

            guild = interaction.guild

            self.bot.tree.copy_global_to(
                guild=guild
            )

            synced = await self.bot.tree.sync(
                guild=guild
            )

            await interaction.followup.send(

                f"✅ Successfully synced "
                f"`{len(synced)}` commands."

            )

        except Exception as e:

            await interaction.followup.send(

                f"❌ Sync failed:\n`{e}`"

            )

    # =========================================================
    # IMPORTANT:
    # HELP COMMAND REMOVED
    # =========================================================
    # The old /help command here was conflicting
    # with your advanced help.py system.
    # Keeping it here breaks slash commands.
    # =========================================================


# =========================================================
# SETUP
# =========================================================

async def setup(bot):

    await bot.add_cog(
        CoreCog(bot)
    )
