import discord
from discord import app_commands
from discord.ext import commands
import asyncio


class StickyCog(commands.Cog):
    def __init__(self, bot):
        self.bot  = bot
        self.locks: dict[str, asyncio.Lock] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def get_lock(self, channel_id: str) -> asyncio.Lock:
        if channel_id not in self.locks:
            self.locks[channel_id] = asyncio.Lock()
        return self.locks[channel_id]

    # ------------------------------------------------------------------
    # /sticky
    # ------------------------------------------------------------------

    @app_commands.command(
        name="sticky",
        description="Pin a message to the bottom of the current channel.",
    )
    @app_commands.describe(
        notice_content="The message text to keep pinned at the bottom of the channel."
    )
    async def sticky(self, interaction: discord.Interaction, notice_content: str):
        if (
            not interaction.user.guild_permissions.manage_messages
            and interaction.user.id not in self.bot.DEVELOPER_IDS
        ):
            return await interaction.response.send_message(
                "❌ You need the Manage Messages permission to use this command.",
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send(
                "❌ Database connection unavailable.", ephemeral=True
            )

        await db_cog.sticky_messages.update_one(
            {"_id": str(interaction.channel_id)},
            {"$set": {"content": notice_content, "last_msg_id": None}},
            upsert=True,
        )
        await interaction.followup.send(
            "✅ Sticky message set successfully.", ephemeral=True
        )

    # ------------------------------------------------------------------
    # /unsticky
    # ------------------------------------------------------------------

    @app_commands.command(
        name="unsticky",
        description="Remove the sticky message from the current channel.",
    )
    async def unsticky(self, interaction: discord.Interaction):
        if (
            not interaction.user.guild_permissions.manage_messages
            and interaction.user.id not in self.bot.DEVELOPER_IDS
        ):
            return await interaction.response.send_message(
                "❌ You need the Manage Messages permission to use this command.",
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send(
                "❌ Database connection unavailable.", ephemeral=True
            )

        await db_cog.sticky_messages.delete_one({"_id": str(interaction.channel_id)})
        await interaction.followup.send(
            "✅ Sticky message removed.", ephemeral=True
        )

    # ------------------------------------------------------------------
    # on_message — repost sticky at the bottom after each new message
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bots and DMs
        if message.author.bot or not message.guild:
            return

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return

        async with self.get_lock(str(message.channel.id)):
            doc = await db_cog.sticky_messages.find_one(
                {"_id": str(message.channel.id)}
            )
            if not doc:
                return

            # Delete the previous sticky message if it exists
            if doc.get("last_msg_id"):
                try:
                    old_msg = await message.channel.fetch_message(
                        int(doc["last_msg_id"])
                    )
                    await old_msg.delete()
                except Exception:
                    pass  # Message may already be deleted

            # Post the new sticky message
            embed = discord.Embed(
                description=doc["content"],
                color=discord.Color.blurple(),
            )
            embed.set_footer(
                text=f"📌 Pinned Notice — {message.guild.name}"
            )
            new_msg = await message.channel.send(embed=embed)

            # Save the new message ID
            await db_cog.sticky_messages.update_one(
                {"_id": str(message.channel.id)},
                {"$set": {"last_msg_id": str(new_msg.id)}},
            )


async def setup(bot):
    await bot.add_cog(StickyCog(bot))
