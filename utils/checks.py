from discord import app_commands


def staff_or_developer(**perms):

    async def predicate(interaction):

        # ============================================
        # Developer Bypass
        # ============================================

        if interaction.user.id in interaction.client.DEVELOPER_IDS:
            return True

        # ============================================
        # Permission Check
        # ============================================

        permissions = interaction.channel.permissions_for(
            interaction.user
        )

        for perm, value in perms.items():

            if getattr(permissions, perm) != value:
                return False

        return True

    return app_commands.check(predicate)
