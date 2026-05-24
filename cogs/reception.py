import discord
from discord import app_commands
from discord.ext import commands


class ReceptionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # /setwelcome
    # ------------------------------------------------------------------

    @app_commands.command(
        name="setwelcome",
        description="Set the welcome message for the linked public server.",
    )
    @app_commands.describe(
        target_channel="The channel where welcome messages will be sent.",
        welcome_message="Welcome message text. Use {user} and {server} as placeholders.",
    )
    async def set_welcome_config(
        self,
        interaction: discord.Interaction,
        target_channel: discord.TextChannel,
        welcome_message: str,
    ):
        if (
            not interaction.user.guild_permissions.administrator
            and interaction.user.id not in self.bot.DEVELOPER_IDS
        ):
            return await interaction.response.send_message(
                "❌ Administrator permission required.", ephemeral=True
            )

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message(
                "❌ Database connection unavailable.", ephemeral=True
            )

        link = await db_cog.get_server_link(interaction.guild.id)
        if not link:
            return await interaction.response.send_message(
                "❌ This command must be run from the Staff Server.", ephemeral=True
            )

        await db_cog.reception.update_one(
            {"guild_id": str(link["public_guild_id"])},
            {
                "$set": {
                    "welcome_channel": str(target_channel.id),
                    "welcome_text":    welcome_message,
                }
            },
            upsert=True,
        )
        await interaction.response.send_message(
            f"✅ Welcome messages will be sent to {target_channel.mention}."
        )

    # ------------------------------------------------------------------
    # /setleave
    # ------------------------------------------------------------------

    @app_commands.command(
        name="setleave",
        description="Set the leave message for the linked public server.",
    )
    @app_commands.describe(
        target_channel="The channel where leave messages will be sent.",
        leave_message="Leave message text. Use {user} and {server} as placeholders.",
    )
    async def set_leave_config(
        self,
        interaction: discord.Interaction,
        target_channel: discord.TextChannel,
        leave_message: str,
    ):
        if (
            not interaction.user.guild_permissions.administrator
            and interaction.user.id not in self.bot.DEVELOPER_IDS
        ):
            return await interaction.response.send_message(
                "❌ Administrator permission required.", ephemeral=True
            )

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message(
                "❌ Database connection unavailable.", ephemeral=True
            )

        link = await db_cog.get_server_link(interaction.guild.id)
        if not link:
            return await interaction.response.send_message(
                "❌ This command must be run from the Staff Server.", ephemeral=True
            )

        await db_cog.reception.update_one(
            {"guild_id": str(link["public_guild_id"])},
            {
                "$set": {
                    "leave_channel": str(target_channel.id),
                    "leave_text":    leave_message,
                }
            },
            upsert=True,
        )
        await interaction.response.send_message(
            f"✅ Leave messages will be sent to {target_channel.mention}."
        )

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return

        cfg = await db_cog.reception.find_one({"guild_id": str(member.guild.id)})
        if cfg and cfg.get("welcome_channel"):
            channel = self.bot.get_channel(int(cfg["welcome_channel"]))
            if channel:
                text = (
                    cfg["welcome_text"]
                    .replace("{user}", member.mention)
                    .replace("{server}", member.guild.name)
                )
                try:
                    await channel.send(text)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return

        cfg = await db_cog.reception.find_one({"guild_id": str(member.guild.id)})
        if cfg and cfg.get("leave_channel"):
            channel = self.bot.get_channel(int(cfg["leave_channel"]))
            if channel:
                text = (
                    cfg["leave_text"]
                    .replace("{user}", member.name)
                    .replace("{server}", member.guild.name)
                )
                try:
                    await channel.send(text)
                except Exception:
                    pass


async def setup(bot):
    await bot.add_cog(ReceptionCog(bot))
