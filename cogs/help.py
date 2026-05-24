import discord
from discord.ext import commands
from discord import app_commands


class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Moderation",
                emoji="🛡️",
                description="View moderation commands."
            ),
            discord.SelectOption(
                label="Modmail",
                emoji="📩",
                description="View modmail commands."
            ),
            discord.SelectOption(
                label="Utility",
                emoji="⚙️",
                description="View utility commands."
            ),
            discord.SelectOption(
                label="Staff",
                emoji="👥",
                description="View staff management commands."
            ),
        ]

        super().__init__(
            placeholder="Select a category...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="help_menu_dropdown"
        )

    async def callback(self, interaction: discord.Interaction):

        category = self.values[0]

        embed = discord.Embed(
            color=discord.Color.blurple()
        )

        # =====================================================
        # MODERATION
        # =====================================================

        if category == "Moderation":

            embed.title = "🛡️ Moderation Commands"

            embed.description = (
                "Commands used by moderators and administrators."
            )

            commands_list = [
                "`/warn` → Warn a member.",
                "`/timeout` → Timeout a member.",
                "`/mute` → Mute a member.",
                "`/kick` → Kick a member.",
                "`/ban` → Ban a member.",
                "`/softban` → Softban a member.",
                "`/purge` → Delete messages.",
                "`/slowmode` → Set slowmode.",
                "`/lock` → Lock a channel.",
                "`/unlock` → Unlock a channel.",
                "`/nickname` → Change nickname.",
                "`/role` → Add or remove roles.",
                "`/history` → View moderation history.",
                "`/setmodlog` → Configure mod logs.",
            ]

            embed.add_field(
                name="Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # MODMAIL
        # =====================================================

        elif category == "Modmail":

            embed.title = "📩 Modmail Commands"

            embed.description = (
                "Support ticket and modmail system commands."
            )

            commands_list = [
                "`/setupmodmail` → Setup modmail system.",
                "`DM the bot` → Open a support ticket.",
                "`Claim Button` → Claim a ticket.",
                "`Close Button` → Close a ticket.",
            ]

            embed.add_field(
                name="Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # UTILITY
        # =====================================================

        elif category == "Utility":

            embed.title = "⚙️ Utility Commands"

            embed.description = (
                "General server utility commands."
            )

            commands_list = [
                "`/sticky` → Create sticky messages.",
                "`/unsticky` → Remove sticky messages.",
                "`/setwelcome` → Configure welcome messages.",
                "`/setleave` → Configure leave messages.",
            ]

            embed.add_field(
                name="Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # STAFF
        # =====================================================

        elif category == "Staff":

            embed.title = "👥 Staff Commands"

            embed.description = (
                "Staff management and quota commands."
            )

            commands_list = [
                "`/setdepartment` → Assign departments.",
                "`/removedepartment` → Remove department.",
                "`/addrank` → Create staff rank.",
                "`/addduty` → Add rank duties.",
                "`/poststaffdropdown` → Post rank menu.",
                "`/deployquotamatrix` → Deploy quota dashboard.",
            ]

            embed.add_field(
                name="Commands",
                value="\n".join(commands_list),
                inline=False
            )

        embed.set_footer(
            text=f"Requested by {interaction.user}",
            icon_url=interaction.user.display_avatar.url
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self.view
        )


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(HelpDropdown())


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # =========================================================
    # /help
    # =========================================================

    @app_commands.command(
        name="help",
        description="View all available bot commands."
    )
    async def help_command(
        self,
        interaction: discord.Interaction
    ):

        embed = discord.Embed(
            title="🤖 Bot Help Menu",
            description=(
                "Welcome to the help menu.\n\n"
                "Use the dropdown below to browse command categories."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="📚 Categories",
            value=(
                "🛡️ Moderation\n"
                "📩 Modmail\n"
                "⚙️ Utility\n"
                "👥 Staff"
            ),
            inline=False
        )

        embed.set_thumbnail(
            url=interaction.guild.icon.url
            if interaction.guild.icon
            else discord.Embed.Empty
        )

        embed.set_footer(
            text=f"{interaction.guild.name}",
            icon_url=interaction.guild.icon.url
            if interaction.guild.icon
            else None
        )

        await interaction.response.send_message(
            embed=embed,
            view=HelpView(),
            ephemeral=False
        )


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
