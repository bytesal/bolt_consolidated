import discord
from discord import app_commands
from discord.ext import commands
from utils.logger import get_logger

logger = get_logger("reaction_roles")


class ReactionRolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="addreactrole", description="Add a reaction role to a message.")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.describe(message_id="ID of the message", emoji="Emoji to react with", role="Role to assign")
    async def add_react_role(self, interaction: discord.Interaction, message_id: str, emoji: str, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        try:
            msg = await interaction.channel.fetch_message(int(message_id))
        except Exception:
            return await interaction.followup.send("❌ Message not found in this channel.", ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database unavailable.", ephemeral=True)
        await db_cog.reaction_roles.update_one(
            {"message_id": str(msg.id), "guild_id": str(interaction.guild.id)},
            {"$set": {emoji: str(role.id)}},
            upsert=True
        )
        try:
            await msg.add_reaction(emoji)
        except Exception:
            return await interaction.followup.send(f"❌ Could not add reaction `{emoji}`.", ephemeral=True)
        await interaction.followup.send(f"✅ Reaction role added: {emoji} → {role.mention}")
        logger.info(f"Reaction role added by {interaction.user.id} in {interaction.guild.id}: {emoji} -> {role.id}")

    @app_commands.command(name="removereactrole", description="Remove a reaction role from a message.")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.describe(message_id="ID of the message", emoji="Emoji to remove")
    async def remove_react_role(self, interaction: discord.Interaction, message_id: str, emoji: str):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database unavailable.", ephemeral=True)
        result = await db_cog.reaction_roles.update_one(
            {"message_id": message_id, "guild_id": str(interaction.guild.id)},
            {"$unset": {emoji: ""}}
        )
        if result.modified_count == 0:
            await interaction.followup.send("❌ No reaction role found for that emoji on that message.", ephemeral=True)
        else:
            await interaction.followup.send(f"✅ Removed reaction role for {emoji}.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return
        doc = await db_cog.reaction_roles.find_one({"message_id": str(payload.message_id), "guild_id": str(payload.guild_id)})
        if not doc:
            return
        emoji_str = str(payload.emoji)
        role_id = doc.get(emoji_str)
        if not role_id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member:
            return
        role = guild.get_role(int(role_id))
        if not role:
            return
        try:
            await member.add_roles(role, reason="Reaction role")
        except Exception as e:
            logger.warning(f"Failed to add reaction role for {payload.user_id}: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return
        doc = await db_cog.reaction_roles.find_one({"message_id": str(payload.message_id), "guild_id": str(payload.guild_id)})
        if not doc:
            return
        emoji_str = str(payload.emoji)
        role_id = doc.get(emoji_str)
        if not role_id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member:
            return
        role = guild.get_role(int(role_id))
        if not role:
            return
        try:
            await member.remove_roles(role, reason="Reaction role removed")
        except Exception as e:
            logger.warning(f"Failed to remove reaction role for {payload.user_id}: {e}")


async def setup(bot):
    await bot.add_cog(ReactionRolesCog(bot))
