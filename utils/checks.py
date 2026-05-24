import discord
from discord import app_commands


# =========================================================
# STAFF / DEVELOPER CHECK SYSTEM
# =========================================================

def staff_or_developer(**perms):

    async def predicate(interaction: discord.Interaction):

        bot = interaction.client

        # =====================================================
        # Developer Global Bypass
        # =====================================================

        if interaction.user.id in bot.DEVELOPER_IDS:
            return True

        db_cog = bot.get_cog("DatabaseCog")

        if not db_cog:
            return False

        # =====================================================
        # Get Staff Guild
        # =====================================================

        config = await db_cog.settings.find_one({
            "_id": "staff_control_guild"
        })

        # =====================================================
        # If No Staff Guild Set
        # Fallback To Normal Guild Permissions
        # =====================================================

        if not config:

            permissions = interaction.channel.permissions_for(
                interaction.user
            )

            for perm, value in perms.items():

                if getattr(permissions, perm) != value:
                    return False

            return True

        # =====================================================
        # Staff Control Guild Lookup
        # =====================================================

        staff_guild_id = int(config["guild_id"])

        staff_guild = bot.get_guild(
            staff_guild_id
        )

        if not staff_guild:
            return False

        # =====================================================
        # Get Member Inside Staff Guild
        # =====================================================

        staff_member = staff_guild.get_member(
            interaction.user.id
        )

        if not staff_member:
            return False

        # =====================================================
        # Check Permissions In STAFF SERVER
        # =====================================================

        permissions = staff_member.guild_permissions

        for perm, value in perms.items():

            if getattr(permissions, perm) != value:
                return False

        return True

    return app_commands.check(predicate)
