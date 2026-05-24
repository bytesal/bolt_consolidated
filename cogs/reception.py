import os
import discord
from discord import app_commands
from discord.ext import commands

class ReceptionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setwelcome", description="Configure public welcome greetings targeted at a specific text channel layout.")
    @app_commands.describe(
        target_channel="The target text channel inside the server deployment architecture.",
        welcome_message="The dynamic text payload layout string (Supports placeholder tokens: {user}, {server})."
    )
    async def set_welcome_config(self, interaction: discord.Interaction, target_channel: discord.TextChannel, welcome_message: str):
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Core DB Connection Unavailable.", ephemeral=True)

        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Missing Admin Privileges.", ephemeral=True)
            
        link = await db_cog.get_server_link(interaction.guild.id)
        if not link:
            return await interaction.response.send_message("❌ System Routing Error: Run this command from within the designated Staff Server.", ephemeral=True)

        await db_cog.reception.update_one(
            {"guild_id": str(link["public_guild_id"])},
            {"$set": {"welcome_channel": str(target_channel.id), "welcome_text": welcome_message}},
            upsert=True
        )
        await interaction.response.send_message(f"✅ Configured: Public greetings map safely to channel {target_channel.mention}.")

    @app_commands.command(name="setleave", description="Configure public departure logs targeted at a specific text channel layout.")
    @app_commands.describe(
        target_channel="The target text channel inside the server deployment architecture.",
        leave_message="The dynamic text payload layout string (Supports placeholder tokens: {user}, {server})."
    )
    async def set_leave_config(self, interaction: discord.Interaction, target_channel: discord.TextChannel, leave_message: str):
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Core DB Connection Unavailable.", ephemeral=True)

        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Missing Admin Privileges.", ephemeral=True)

        link = await db_cog.get_server_link(interaction.guild.id)
        if not link:
            return await interaction.response.send_message("❌ System Routing Error: Run this command from within the designated Staff Server.", ephemeral=True)

        await db_cog.reception.update_one(
            {"guild_id": str(link["public_guild_id"])},
            {"$set": {"leave_channel": str(target_channel.id), "leave_text": leave_message}},
            upsert=True
        )
        await interaction.response.send_message(f"✅ Configured: Public departures map safely to channel {target_channel.mention}.")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return
            
        cfg = await db_cog.reception.find_one({"guild_id": str(member.guild.id)})
        if cfg and cfg.get("welcome_channel"):
            channel = self.bot.get_channel(int(cfg["welcome_channel"]))
            if channel:
                text = cfg["welcome_text"].replace("{user}", member.mention).replace("{server}", member.guild.name)
                try:
                    await channel.send(text)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return
            
        cfg = await db_cog.reception.find_one({"guild_id": str(member.guild.id)})
        if cfg and cfg.get("leave_channel"):
            channel = self.bot.get_channel(int(cfg["leave_channel"]))
            if channel:
                text = cfg["leave_text"].replace("{user}", member.name).replace("{server}", member.guild.name)
                try:
                    await channel.send(text)
                except Exception:
                    pass

async def setup(bot):
    await bot.add_cog(ReceptionCog(bot))
