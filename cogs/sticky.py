import os
import discord
from discord import app_commands
from discord.ext import commands
import asyncio

class StickyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.locks = {}

    def get_lock(self, channel_id: str):
        if channel_id not in self.locks:
            self.locks[channel_id] = asyncio.Lock()
        return self.locks[channel_id]

    @app_commands.command(name="sticky", description="Affix dynamic notice text block down bottom stream boundary layers.")
    @app_commands.describe(notice_content="The structured text notice payload to stick to the bottom of the viewport.")
    async def sticky(self, interaction: discord.Interaction, notice_content: str):
        if not interaction.user.guild_permissions.manage_messages and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Privilege Metric Verification Failed.", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Core DB Connection Unavailable.", ephemeral=True)
            
        await db_cog.sticky_messages.update_one(
            {"_id": str(interaction.channel_id)},
            {"$set": {"content": notice_content, "last_msg_id": None}},
            upsert=True
        )
        await interaction.followup.send("✅ Sticky context boundary parameters established safely.", ephemeral=True)

    @app_commands.command(name="unsticky", description="Purge notice binding metrics completely from local view matrix.")
    async def unsticky(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_messages and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Privilege Metric Verification Failed.", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Core DB Connection Unavailable.", ephemeral=True)
            
        await db_cog.sticky_messages.delete_one({"_id": str(interaction.channel_id)})
        await interaction.followup.send("✅ Sticky properties dropped cleanly from target region.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
            
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return

        async with self.get_lock(str(message.channel.id)):
            doc = await db_cog.sticky_messages.find_one({"_id": str(message.channel.id)})
            if not doc:
                return

            if doc.get("last_msg_id"):
                try:
                    old_msg = await message.channel.fetch_message(int(doc["last_msg_id"]))
                    await old_msg.delete()
                except Exception:
                    pass

            embed = discord.Embed(description=doc["content"], color=discord.Color.blurple())
            embed.set_footer(text=f"📌 Fixed Information Notice Frame — {message.guild.name}")
            new_msg = await message.channel.send(embed=embed)
            
            await db_cog.sticky_messages.update_one(
                {"_id": str(message.channel.id)},
                {"$set": {"last_msg_id": str(new_msg.id)}}
            )

async def setup(bot):
    await bot.add_cog(StickyCog(bot))
