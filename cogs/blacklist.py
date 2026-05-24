import discord
from discord import app_commands
from discord.ext import commands


class BlacklistCog(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # =====================================================
    # CHECKS
    # =====================================================

    def is_dev(self, user_id):

        return (
            user_id
            in self.bot.DEVELOPER_IDS
        )

    # =====================================================
    # BLACKLIST USER
    # =====================================================

    @app_commands.command(
        name="blacklistuser",
        description="Blacklist a user globally."
    )
    async def blacklist_user(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        reason: str
    ):

        if not self.is_dev(
            interaction.user.id
        ):

            return await interaction.response.send_message(
                "❌ Developer only.",
                ephemeral=True
            )

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        await db_cog.blacklist.update_one(

            {
                "_id": str(user.id)
            },

            {
                "$set": {
                    "type": "user",
                    "reason": reason
                }
            },

            upsert=True
        )

        await interaction.response.send_message(
            f"✅ Blacklisted user: "
            f"{user}"
        )

    # =====================================================
    # UNBLACKLIST USER
    # =====================================================

    @app_commands.command(
        name="unblacklistuser",
        description="Remove blacklist from a user."
    )
    async def unblacklist_user(
        self,
        interaction: discord.Interaction,
        user: discord.User
    ):

        if not self.is_dev(
            interaction.user.id
        ):

            return await interaction.response.send_message(
                "❌ Developer only.",
                ephemeral=True
            )

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        await db_cog.blacklist.delete_one({
            "_id": str(user.id)
        })

        await interaction.response.send_message(
            f"✅ Removed blacklist from "
            f"{user}"
        )

    # =====================================================
    # BLACKLIST GUILD
    # =====================================================

    @app_commands.command(
        name="blacklistguild",
        description="Blacklist a guild globally."
    )
    async def blacklist_guild(
        self,
        interaction: discord.Interaction,
        guild_id: str,
        reason: str
    ):

        if not self.is_dev(
            interaction.user.id
        ):

            return await interaction.response.send_message(
                "❌ Developer only.",
                ephemeral=True
            )

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        await db_cog.blacklist.update_one(

            {
                "_id": guild_id
            },

            {
                "$set": {
                    "type": "guild",
                    "reason": reason
                }
            },

            upsert=True
        )

        await interaction.response.send_message(
            f"✅ Blacklisted guild: "
            f"`{guild_id}`"
        )

    # =====================================================
    # UNBLACKLIST GUILD
    # =====================================================

    @app_commands.command(
        name="unblacklistguild",
        description="Remove blacklist from guild."
    )
    async def unblacklist_guild(
        self,
        interaction: discord.Interaction,
        guild_id: str
    ):

        if not self.is_dev(
            interaction.user.id
        ):

            return await interaction.response.send_message(
                "❌ Developer only.",
                ephemeral=True
            )

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        await db_cog.blacklist.delete_one({
            "_id": guild_id
        })

        await interaction.response.send_message(
            f"✅ Removed blacklist from "
            f"`{guild_id}`"
        )


async def setup(bot):

    await bot.add_cog(
        BlacklistCog(bot)
    )
