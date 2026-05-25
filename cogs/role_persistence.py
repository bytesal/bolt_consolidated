import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from utils.logger import get_logger

logger = get_logger("role_persistence")


class RolePersistenceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Store member's roles when they leave (excluding temporary roles)."""
        if member.bot:
            return
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return

        # Exclude @everyone and roles that are likely temporary (configurable)
        exclude_role_names = ["Muted", "Guest", "Temp", "Verification"]
        role_ids = [role.id for role in member.roles
                    if role != member.guild.default_role
                    and role.name not in exclude_role_names
                    and not role.is_premium_subscriber()]  # exclude boost role

        if not role_ids:
            return

        backup = {
            "user_id": str(member.id),
            "guild_id": str(member.guild.id),
            "roles": role_ids,
            "created_at": datetime.utcnow()
        }
        await db_cog.role_backup.update_one(
            {"user_id": str(member.id), "guild_id": str(member.guild.id)},
            {"$set": backup},
            upsert=True
        )
        logger.info(f"Stored role backup for user {member.id} in guild {member.guild.id}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Restore roles when a member rejoins."""
        if member.bot:
            return
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return

        backup = await db_cog.role_backup.find_one({
            "user_id": str(member.id),
            "guild_id": str(member.guild.id)
        })
        if not backup:
            return

        role_ids = backup.get("roles", [])
        roles_to_restore = []
        for role_id in role_ids:
            role = member.guild.get_role(role_id)
            if role and role < member.guild.me.top_role:  # bot must be able to assign
                roles_to_restore.append(role)

        if roles_to_restore:
            try:
                await member.add_roles(*roles_to_restore, reason="Role persistence on rejoin")
                logger.info(f"Restored {len(roles_to_restore)} roles for {member.id} in {member.guild.id}")
            except discord.Forbidden:
                logger.warning(f"Missing permissions to restore roles for {member.id}")
            except Exception as e:
                logger.error(f"Failed to restore roles for {member.id}: {e}")

        # Delete backup after restoration
        await db_cog.role_backup.delete_one({
            "user_id": str(member.id),
            "guild_id": str(member.guild.id)
        })

    @app_commands.command(name="restoreroles", description="Manually restore roles for a user (if automatic failed).")
    @app_commands.default_permissions(manage_roles=True)
    async def restore_roles_command(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database error.", ephemeral=True)

        backup = await db_cog.role_backup.find_one({
            "user_id": str(user.id),
            "guild_id": str(interaction.guild.id)
        })
        if not backup:
            return await interaction.followup.send("❌ No role backup found for this user.", ephemeral=True)

        member = interaction.guild.get_member(user.id)
        if not member:
            return await interaction.followup.send("❌ User is not in this server.", ephemeral=True)

        role_ids = backup.get("roles", [])
        roles_to_restore = []
        for role_id in role_ids:
            role = interaction.guild.get_role(role_id)
            if role and role < interaction.guild.me.top_role:
                roles_to_restore.append(role)

        if not roles_to_restore:
            return await interaction.followup.send("❌ No valid roles to restore (maybe they were deleted or are higher than bot).", ephemeral=True)

        try:
            await member.add_roles(*roles_to_restore, reason="Manual role restoration")
            await db_cog.role_backup.delete_one({"_id": backup["_id"]})
            await interaction.followup.send(f"✅ Restored {len(roles_to_restore)} roles for {user.mention}")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(RolePersistenceCog(bot))
