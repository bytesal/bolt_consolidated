import discord
from discord.ext import commands
from discord import app_commands


class ServerLinkCog(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # =====================================================
    # Developer Check
    # =====================================================

    def is_developer(
        self,
        user_id: int
    ):

        return (
            user_id
            in self.bot.DEVELOPER_IDS
        )

    # =====================================================
    # /LINKSERVERS
    # =====================================================

    @app_commands.command(
        name="linkservers",
        description=(
            "Link a staff server "
            "with a public server."
        )
    )

    async def linkservers(
        self,
        interaction: discord.Interaction,
        staff_server_id: str,
        public_server_id: str
    ):

        if not self.is_developer(
            interaction.user.id
        ):

            return await interaction.response.send_message(
                "❌ You are not a developer.",
                ephemeral=True
            )

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        if not db_cog:

            return await interaction.response.send_message(
                "❌ Database system unavailable.",
                ephemeral=True
            )

        await db_cog.link_servers(

            int(staff_server_id),
            int(public_server_id)
        )

        embed = discord.Embed(
            title="🔗 Servers Linked",
            color=discord.Color.green()
        )

        embed.add_field(
            name="Staff Server",
            value=f"`{staff_server_id}`",
            inline=False
        )

        embed.add_field(
            name="Public Server",
            value=f"`{public_server_id}`",
            inline=False
        )

        await interaction.response.send_message(
            embed=embed
        )

    # =====================================================
    # /UNLINKSERVERS
    # =====================================================

    @app_commands.command(
        name="unlinkservers",
        description="Unlink linked servers."
    )

    async def unlinkservers(
        self,
        interaction: discord.Interaction,
        staff_server_id: str
    ):

        if not self.is_developer(
            interaction.user.id
        ):

            return await interaction.response.send_message(
                "❌ You are not a developer.",
                ephemeral=True
            )

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        if not db_cog:

            return await interaction.response.send_message(
                "❌ Database unavailable.",
                ephemeral=True
            )

        await db_cog.unlink_servers(
            int(staff_server_id)
        )

        await interaction.response.send_message(
            (
                "✅ Server link removed "
                "successfully."
            )
        )

    # =====================================================
    # /VIEWLINK
    # =====================================================

    @app_commands.command(
        name="viewlink",
        description="View linked server."
    )

    async def viewlink(
        self,
        interaction: discord.Interaction
    ):

        if not self.is_developer(
            interaction.user.id
        ):

            return await interaction.response.send_message(
                "❌ You are not a developer.",
                ephemeral=True
            )

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        if not db_cog:

            return await interaction.response.send_message(
                "❌ Database unavailable.",
                ephemeral=True
            )

        data = await db_cog.get_server_link(
            interaction.guild.id
        )

        if not data:

            return await interaction.response.send_message(
                "❌ No linked server found.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="🔗 Linked Server",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Staff Server",
            value=f"`{data['staff_guild_id']}`",
            inline=False
        )

        embed.add_field(
            name="Public Server",
            value=f"`{data['public_guild_id']}`",
            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


async def setup(bot):

    await bot.add_cog(
        ServerLinkCog(bot)
    )
