import discord
from discord import app_commands
from discord.ext import commands


# ---------------------------------------------------------------------------
# Dropdown select menu for command categories
# ---------------------------------------------------------------------------

class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Moderation System",
                description="View all moderation and enforcement commands.",
                emoji="⚠️",
            ),
            discord.SelectOption(
                label="Support & Modmail",
                description="View ticketing and support commands.",
                emoji="✉️",
            ),
            discord.SelectOption(
                label="Staff & Quotas",
                description="View staff management and shift commands.",
                emoji="💼",
            ),
            discord.SelectOption(
                label="System & Utility",
                description="View core setup and utility commands.",
                emoji="⚙️",
            ),
        ]
        super().__init__(
            placeholder="Select a category to view its commands...",
            options=options,
            custom_id="bolt_help_dropdown_persistent",
        )

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        embed = discord.Embed(color=discord.Color.teal())

        if selection == "Moderation System":
            embed.title = "⚠️ Moderation Commands"
            embed.description = (
                "`/warn <user> <reason> [evidence]` — Issue a formal warning to a user.\n"
                "`/adwarn <user> <reason> [evidence]` — Issue an advertising policy warning.\n"
                "`/history <user>` — View a user's moderation history."
            )

        elif selection == "Support & Modmail":
            embed.title = "✉️ Support & Modmail Commands"
            embed.description = (
                "`/staffstats` — View staff ticket resolution statistics.\n"
                "*Support sessions are handled automatically via DMs.*"
            )

        elif selection == "Staff & Quotas":
            embed.title = "💼 Staff & Quota Commands"
            embed.description = (
                "`/setdepartment <member> <department>` — Assign a staff member to a department.\n"
                "`/removedepartment <member>` — Remove a member from their department.\n"
                "`/addrank <name> <emoji> <description>` — Create a new staff rank profile.\n"
                "`/addduty <rank> <duty>` — Add a duty requirement to an existing rank.\n"
                "`/poststaffdropdown` — Post the staff ranks overview dropdown.\n"
                "`/deployquotamatrix` — Deploy the shift and quota tracking dashboard."
            )

        elif selection == "System & Utility":
            embed.title = "⚙️ System & Utility Commands"
            embed.description = (
                "`/rank [member]` — Check a member's level and XP.\n"
                "`/sticky <message>` — Pin a message to the bottom of the channel.\n"
                "`/unsticky` — Remove the sticky message from the channel.\n"
                "`/setwelcome <channel> <message>` — Set the welcome message.\n"
                "`/setleave <channel> <message>` — Set the leave message.\n"
                "`/deployappform <job>` — Deploy an application form to the public server.\n"
                "`/hrlogs [reviewer]` — View HR application decision logs.\n"
                "`/sethrchannel` — Set the current channel as the HR log channel."
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class HelpDropdownView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HelpDropdown())


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="helpme",
        description="Open the interactive Bolt command directory.",
    )
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚡ Bolt — Command Directory",
            description=(
                "Welcome to **Bolt**, your all-in-one multi-server management bot.\n\n"
                "Use the dropdown menu below to browse commands by category."
            ),
            color=discord.Color.gold(),
        )
        embed.set_thumbnail(
            url=self.bot.user.display_avatar.url if self.bot.user else None
        )
        embed.set_footer(text="Bolt Multi-Server Bot — Authorized Access Only")

        await interaction.response.send_message(
            embed=embed, view=HelpDropdownView(), ephemeral=True
        )


async def setup(bot):
    # Disable the default prefix help command to avoid conflicts
    if bot.help_command:
        bot.help_command = None
    await bot.add_cog(HelpCog(bot))
