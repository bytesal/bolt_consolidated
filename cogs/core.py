import discord
from discord import app_commands
from discord.ext import commands


class CoreCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def is_dev(self, user_id: int) -> bool:
        return user_id in self.bot.DEVELOPER_IDS

    async def clean_permission_check(
        self, interaction: discord.Interaction, perm: str = None
    ) -> bool:
        """Return True if the user is a developer, has the specified permission,
        or is an administrator."""
        if self.is_dev(interaction.user.id):
            return True
        if perm and hasattr(interaction.user.guild_permissions, perm):
            return getattr(interaction.user.guild_permissions, perm)
        return interaction.user.guild_permissions.administrator

    # ------------------------------------------------------------------
    # /linkserver
    # ------------------------------------------------------------------

    @app_commands.command(
        name="linkserver",
        description="Link this staff server to a public server by its ID.",
    )
    @app_commands.describe(public_guild_id="The numeric ID of the target public server.")
    async def link_server_command(
        self, interaction: discord.Interaction, public_guild_id: str
    ):
        if not await self.clean_permission_check(interaction):
            return await interaction.response.send_message(
                "❌ Administrator permission or Developer identity required.", ephemeral=True
            )

        try:
            target_id = int(public_guild_id)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Invalid server ID. Please provide a valid numeric Discord server ID.",
                ephemeral=True,
            )

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message(
                "❌ Database connection unavailable.", ephemeral=True
            )

        await db_cog.link_servers(interaction.guild.id, target_id)

        embed = discord.Embed(
            title="✅ Server Link Established",
            description=(
                f"This server has been set as the **Staff Server**.\n"
                f"Linked Public Server ID: `{target_id}`"
            ),
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------
    # /setprefix
    # ------------------------------------------------------------------

    @app_commands.command(
        name="setprefix",
        description="Change the bot's command prefix for this server.",
    )
    @app_commands.describe(prefix="The new prefix character(s) to use.")
    async def set_prefix_command(self, interaction: discord.Interaction, prefix: str):
        if not await self.clean_permission_check(interaction):
            return await interaction.response.send_message(
                "❌ Administrator permission required.", ephemeral=True
            )

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message(
                "❌ Database connection unavailable.", ephemeral=True
            )

        await db_cog.set_guild_prefix(interaction.guild.id, prefix)
        await interaction.response.send_message(
            f"✅ Prefix updated to `{prefix}` for this server."
        )

    # ------------------------------------------------------------------
    # /botstatus  (developer only)
    # ------------------------------------------------------------------

    @app_commands.command(
        name="botstatus",
        description="[Developer only] Change the bot's presence status and activity.",
    )
    @app_commands.describe(
        status_type="Status type: online, idle, dnd, or invisible.",
        activity_text="Text to display as the bot's activity.",
    )
    async def bot_status_command(
        self, interaction: discord.Interaction, status_type: str, activity_text: str
    ):
        if not self.is_dev(interaction.user.id):
            return await interaction.response.send_message(
                "❌ This command is restricted to bot developers.", ephemeral=True
            )

        status_map = {
            "online":    discord.Status.online,
            "idle":      discord.Status.idle,
            "dnd":       discord.Status.dnd,
            "invisible": discord.Status.invisible,
        }
        status = status_map.get(status_type.lower(), discord.Status.online)
        await self.bot.change_presence(
            status=status, activity=discord.Game(name=activity_text)
        )
        await interaction.response.send_message(
            "✅ Bot presence updated successfully.", ephemeral=True
        )

    # ------------------------------------------------------------------
    # /setbotname  (developer only)
    # ------------------------------------------------------------------

    @app_commands.command(
        name="setbotname",
        description="[Developer only] Rename the bot's Discord account.",
    )
    @app_commands.describe(new_name="The new username for the bot.")
    async def set_bot_name_command(
        self, interaction: discord.Interaction, new_name: str
    ):
        if not self.is_dev(interaction.user.id):
            return await interaction.response.send_message(
                "❌ This command is restricted to bot developers.", ephemeral=True
            )

        try:
            await self.bot.user.edit(username=new_name)
            await interaction.response.send_message(
                f"✅ Bot username changed to: **{new_name}**"
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to rename the bot: {e}", ephemeral=True
            )

    # ------------------------------------------------------------------
    # /help
    # ------------------------------------------------------------------

    @app_commands.command(
        name="help",
        description="View available commands for this server.",
    )
    async def comprehensive_help(self, interaction: discord.Interaction):
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message(
                "❌ Database connection unavailable.", ephemeral=True
            )

        is_staff  = await db_cog.get_server_link(interaction.guild.id)
        is_public = await db_cog.get_link_by_public(interaction.guild.id)

        embed = discord.Embed(
            title="⚡ Bolt Bot — Command Directory",
            description="Commands available for your current server context.",
            color=discord.Color.blue(),
        )

        if is_staff or self.is_dev(interaction.user.id):
            embed.add_field(
                name="🛡️ Staff Server Commands",
                value=(
                    "`/linkserver <Public ID>` — Link this server to a public server\n"
                    "`/setprefix <Symbol>` — Change the bot prefix\n"
                    "`/setwelcome <Channel> <Message>` — Set welcome message\n"
                    "`/setleave <Channel> <Message>` — Set leave message\n"
                    "`/sethrchannel` — Set the HR log channel\n"
                    "`/deployappform <Job>` — Deploy an application form\n"
                    "`/hrlogs [Staff]` — View HR decision logs\n"
                    "`/addrank <Name> <Emoji> <Description>` — Add a staff rank\n"
                    "`/addduty <Rank> <Duty>` — Add a duty to a rank\n"
                    "`/removedepartment <Member>` — Remove member from department\n"
                    "`/shift` / `/quota` — View shift and quota tools"
                ),
                inline=False,
            )

        if is_public or not is_staff:
            embed.add_field(
                name="🌍 Public Server Commands",
                value=(
                    "`/rank` — Check your level and XP\n"
                    "`/apply` — Apply for a staff position\n"
                    "`/warn` / `/adwarn` — Issue warnings (moderators only)\n"
                    "`/sticky` — Pin a message to the bottom of a channel"
                ),
                inline=False,
            )

        if self.is_dev(interaction.user.id):
            embed.add_field(
                name="🔧 Developer Commands",
                value=(
                    "`/botstatus <Type> <Text>` — Change bot presence\n"
                    "`/setbotname <Name>` — Rename the bot"
                ),
                inline=False,
            )

        embed.set_footer(text="Bolt Multi-Server Bot • v2.5")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(CoreCog(bot))
