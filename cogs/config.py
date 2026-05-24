import discord
from discord.ext import commands
from discord import app_commands


class ConfigCog(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # =====================================================
    # DEVELOPER CHECK
    # =====================================================

    def is_developer(
        self,
        interaction: discord.Interaction
    ):

        return (
            interaction.user.id
            in self.bot.DEVELOPER_IDS
        )

    # =====================================================
    # SET MAIN SERVER
    # =====================================================

    @app_commands.command(
        name="setmainserver",
        description="Set the main community server."
    )
    async def set_main_server(
        self,
        interaction: discord.Interaction
    ):

        if not self.is_developer(interaction):

            return await interaction.response.send_message(
                "❌ Developer only.",
                ephemeral=True
            )

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        await db_cog.settings.update_one(

            {
                "_id": "main_server"
            },

            {
                "$set": {
                    "guild_id": str(
                        interaction.guild.id
                    )
                }
            },

            upsert=True
        )

        await interaction.response.send_message(

            f"✅ Main server set to:\n"
            f"`{interaction.guild.name}`",

            ephemeral=True
        )

    # =====================================================
    # SET STAFF SERVER
    # =====================================================

    @app_commands.command(
        name="setstaffserver",
        description="Set the staff control server."
    )
    async def set_staff_server(
        self,
        interaction: discord.Interaction
    ):

        if not self.is_developer(interaction):

            return await interaction.response.send_message(
                "❌ Developer only.",
                ephemeral=True
            )

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        await db_cog.settings.update_one(

            {
                "_id": "staff_server"
            },

            {
                "$set": {
                    "guild_id": str(
                        interaction.guild.id
                    )
                }
            },

            upsert=True
        )

        await interaction.response.send_message(

            f"✅ Staff server set to:\n"
            f"`{interaction.guild.name}`",

            ephemeral=True
        )

    # =====================================================
    # VIEW CONFIG
    # =====================================================

    @app_commands.command(
        name="viewconfig",
        description="View current bot configuration."
    )
    async def view_config(
        self,
        interaction: discord.Interaction
    ):

        if not self.is_developer(interaction):

            return await interaction.response.send_message(
                "❌ Developer only.",
                ephemeral=True
            )

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        main_server = await db_cog.settings.find_one({
            "_id": "main_server"
        })

        staff_server = await db_cog.settings.find_one({
            "_id": "staff_server"
        })

        embed = discord.Embed(

            title="⚙️ Bot Configuration",

            color=discord.Color.blurple()
        )

        # =================================================
        # MAIN SERVER
        # =================================================

        if main_server:

            guild = self.bot.get_guild(
                int(main_server["guild_id"])
            )

            embed.add_field(

                name="🌐 Main Server",

                value=(
                    f"{guild.name}\n"
                    f"`{guild.id}`"
                )
                if guild
                else "Unknown",

                inline=False
            )

        else:

            embed.add_field(
                name="🌐 Main Server",
                value="Not configured.",
                inline=False
            )

        # =================================================
        # STAFF SERVER
        # =================================================

        if staff_server:

            guild = self.bot.get_guild(
                int(staff_server["guild_id"])
            )

            embed.add_field(

                name="🛠️ Staff Server",

                value=(
                    f"{guild.name}\n"
                    f"`{guild.id}`"
                )
                if guild
                else "Unknown",

                inline=False
            )

        else:

            embed.add_field(
                name="🛠️ Staff Server",
                value="Not configured.",
                inline=False
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # =====================================================
    # RESET CONFIG
    # =====================================================

    @app_commands.command(
        name="resetconfig",
        description="Reset bot configuration."
    )
    async def reset_config(
        self,
        interaction: discord.Interaction
    ):

        if not self.is_developer(interaction):

            return await interaction.response.send_message(
                "❌ Developer only.",
                ephemeral=True
            )

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        await db_cog.settings.delete_many({

            "_id": {
                "$in": [
                    "main_server",
                    "staff_server"
                ]
            }
        })

        await interaction.response.send_message(

            "✅ Configuration reset successfully.",

            ephemeral=True
        )


async def setup(bot):

    await bot.add_cog(
        ConfigCog(bot)
    )
