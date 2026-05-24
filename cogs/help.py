import discord
from discord.ext import commands
from discord import app_commands


# =========================================================
# HELP DROPDOWN
# =========================================================

class HelpDropdown(discord.ui.Select):

    def __init__(self):

        options = [

            discord.SelectOption(
                label="Moderation",
                emoji="🛡️",
                description="Moderation and punishment commands."
            ),

            discord.SelectOption(
                label="Modmail",
                emoji="📩",
                description="Support and ticket system commands."
            ),

            discord.SelectOption(
                label="Reception",
                emoji="🎉",
                description="Welcome and reception system."
            ),

            discord.SelectOption(
                label="Applications",
                emoji="📄",
                description="Applications and recruitment system."
            ),

            discord.SelectOption(
                label="Leveling",
                emoji="📈",
                description="XP and leveling commands."
            ),

            discord.SelectOption(
                label="Utility",
                emoji="⚙️",
                description="Utility and management commands."
            ),

            discord.SelectOption(
                label="Staff",
                emoji="👥",
                description="Staff systems and quota commands."
            ),

            discord.SelectOption(
                label="Staff Teams",
                emoji="📂",
                description="Dynamic staff department system."
            ),

            discord.SelectOption(
                label="AutoMod",
                emoji="🤖",
                description="Automatic moderation system."
            ),

            discord.SelectOption(
                label="Analytics",
                emoji="📊",
                description="Statistics and analytics commands."
            ),

            discord.SelectOption(
                label="Server Linking",
                emoji="🔗",
                description="Cross-server management commands."
            ),

            discord.SelectOption(
                label="Developer",
                emoji="🧑‍💻",
                description="Developer-only commands."
            ),
        ]

        super().__init__(
            placeholder="Select a command category...",
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
                "Cross-server moderation commands "
                "used by staff members."
            )

            commands_list = [

                "`/warn` → Warn a member.",
                "`/timeout` → Timeout a member.",
                "`/kick` → Kick a member.",
                "`/ban` → Ban a member.",
                "`/history` → View moderation history.",
                "`/setmodlog` → Configure moderation logs.",
                "`/purge` → Delete messages.",
                "`/purgeuser` → Delete messages from a user.",
            ]

            embed.add_field(
                name="Available Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # MODMAIL
        # =====================================================

        elif category == "Modmail":

            embed.title = "📩 Modmail Commands"

            embed.description = (
                "Professional support ticket system."
            )

            commands_list = [

                "`/setupmodmail` → Configure modmail category.",
                "`/panel` → Send modmail panel.",
                "`DM the bot` → Create a support ticket.",
                "`Claim Button` → Claim a ticket.",
                "`Close Button` → Close a ticket.",
            ]

            embed.add_field(
                name="Available Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # RECEPTION
        # =====================================================

        elif category == "Reception":

            embed.title = "🎉 Reception Commands"

            embed.description = (
                "Reception and onboarding systems."
            )

            commands_list = [

                "`/setwelcome` → Configure welcome messages.",
                "`/setleave` → Configure leave messages.",
                "`/setautorole` → Configure autoroles.",
                "`/setruleschannel` → Configure rules channel.",
            ]

            embed.add_field(
                name="Available Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # APPLICATIONS
        # =====================================================

        elif category == "Applications":

            embed.title = "📄 Application Commands"

            embed.description = (
                "Applications and recruitment system."
            )

            commands_list = [

                "`/applicationpanel` → Send application panel.",
                "`/createapplication` → Create an application.",
                "`/applications` → View applications.",
                "`/acceptapplication` → Accept an application.",
                "`/denyapplication` → Deny an application.",
            ]

            embed.add_field(
                name="Available Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # LEVELING
        # =====================================================

        elif category == "Leveling":

            embed.title = "📈 Leveling Commands"

            embed.description = (
                "XP and ranking system commands."
            )

            commands_list = [

                "`/rank` → View user rank.",
                "`/leaderboard` → View XP leaderboard.",
                "`/setlevelchannel` → Configure level-up channel.",
                "`/setxprate` → Configure XP gain rate.",
            ]

            embed.add_field(
                name="Available Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # UTILITY
        # =====================================================

        elif category == "Utility":

            embed.title = "⚙️ Utility Commands"

            embed.description = (
                "General utility and management commands."
            )

            commands_list = [

                "`/sticky` → Create sticky messages.",
                "`/unsticky` → Remove sticky messages.",
                "`/ping` → View bot latency.",
                "`/serverinfo` → View server information.",
            ]

            embed.add_field(
                name="Available Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # STAFF
        # =====================================================

        elif category == "Staff":

            embed.title = "👥 Staff Commands"

            embed.description = (
                "Staff management and quota systems."
            )

            commands_list = [

                "`/setdepartment` → Assign departments.",
                "`/removedepartment` → Remove departments.",
                "`/addrank` → Create staff ranks.",
                "`/addduty` → Add rank duties.",
                "`/poststaffdropdown` → Post ranks dropdown.",
                "`/deployquotamatrix` → Deploy quota dashboard.",
            ]

            embed.add_field(
                name="Available Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # STAFF TEAMS
        # =====================================================

        elif category == "Staff Teams":

            embed.title = "📂 Staff Team Commands"

            embed.description = (
                "Dynamic staff department system."
            )

            commands_list = [

                "`/createteam` → Create a staff team.",
                "`/addmember` → Add a member to a team.",
                "`/removemember` → Remove a member from a team.",
                "`/addresponsibility` → Add responsibilities to a team.",
                "`/poststaffpanel` → Deploy the public staff panel.",
            ]

            embed.add_field(
                name="Available Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # AUTOMOD
        # =====================================================

        elif category == "AutoMod":

            embed.title = "🤖 AutoMod Commands"

            embed.description = (
                "Automatic moderation configuration."
            )

            commands_list = [

                "`!automod links true/false` → Toggle anti-links.",
                "`!automod spam true/false` → Toggle anti-spam.",
                "`!automod mentions true/false` → Toggle mention protection.",
                "`!allowads` → Allow advertisements in channel.",
                "`!removeads` → Remove advertisement permissions.",
            ]

            embed.add_field(
                name="Available Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # ANALYTICS
        # =====================================================

        elif category == "Analytics":

            embed.title = "📊 Analytics Commands"

            embed.description = (
                "Bot statistics and analytics."
            )

            commands_list = [

                "`/dashboard` → View analytics dashboard.",
                "`/botstats` → View detailed bot statistics.",
            ]

            embed.add_field(
                name="Available Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # SERVER LINKING
        # =====================================================

        elif category == "Server Linking":

            embed.title = "🔗 Server Linking Commands"

            embed.description = (
                "Cross-server infrastructure management."
            )

            commands_list = [

                "`/linkservers` → Link staff and public servers.",
                "`/unlinkservers` → Remove linked servers.",
                "`/viewlink` → View current linked servers.",
            ]

            embed.add_field(
                name="Available Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # DEVELOPER
        # =====================================================

        elif category == "Developer":

            if interaction.user.id not in interaction.client.DEVELOPER_IDS:

                embed.title = "🔒 Restricted Category"

                embed.description = (
                    "You do not have permission "
                    "to access developer commands."
                )

                embed.color = discord.Color.red()

                embed.set_footer(
                    text="Developer Access Required"
                )

                return await interaction.response.edit_message(
                    embed=embed,
                    view=self.view
                )

            embed.title = "🧑‍💻 Developer Commands"

            embed.description = (
                "Developer-only management commands."
            )

            commands_list = [

                "`/sync` → Sync application commands.",
                "`/reload` → Reload a cog.",
                "`/load` → Load a cog.",
                "`/unload` → Unload a cog.",
                "`/shutdown` → Shutdown the bot.",
                "`/eval` → Execute Python code.",
                "`/devpanel` → Open developer panel.",
                "`/blacklistuser` → Blacklist a user globally.",
                "`/unblacklistuser` → Remove user blacklist.",
                "`/blacklistguild` → Blacklist a guild globally.",
                "`/unblacklistguild` → Remove guild blacklist.",
            ]

            embed.add_field(
                name="Available Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # FINAL STYLING
        # =====================================================

        embed.set_footer(
            text=f"Requested by {interaction.user}",
            icon_url=interaction.user.display_avatar.url
        )

        embed.timestamp = discord.utils.utcnow()

        await interaction.response.edit_message(
            embed=embed,
            view=self.view
        )


# =========================================================
# HELP VIEW
# =========================================================

class HelpView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

        self.add_item(
            HelpDropdown()
        )


# =========================================================
# HELP COG
# =========================================================

class HelpCog(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    # =====================================================
    # /HELP
    # =====================================================

    @app_commands.command(
        name="help",
        description="View all available bot commands."
    )

    async def help_command(
        self,
        interaction: discord.Interaction
    ):

        embed = discord.Embed(

            title="🤖 Bolt Engine Help Center",

            description=(

                "Welcome to the interactive help system.\n\n"

                "Use the dropdown menu below "
                "to browse all command categories."

            ),

            color=discord.Color.blurple()
        )

        embed.add_field(

            name="📚 Command Categories",

            value=(

                "🛡️ Moderation\n"
                "📩 Modmail\n"
                "🎉 Reception\n"
                "📄 Applications\n"
                "📈 Leveling\n"
                "⚙️ Utility\n"
                "👥 Staff\n"
                "📂 Staff Teams\n"
                "🤖 AutoMod\n"
                "📊 Analytics\n"
                "🔗 Server Linking\n"
                "🧑‍💻 Developer"

            ),

            inline=False
        )

        embed.add_field(

            name="✨ Features",

            value=(

                "• Cross-Server Moderation\n"
                "• Linked Server Infrastructure\n"
                "• Persistent Systems\n"
                "• Professional Modmail\n"
                "• Dynamic Staff Teams\n"
                "• Staff Analytics\n"
                "• Advanced AutoMod"

            ),

            inline=False
        )

        if interaction.guild.icon:

            embed.set_thumbnail(
                url=interaction.guild.icon.url
            )

        embed.set_footer(

            text=f"{interaction.guild.name}",

            icon_url=(
                interaction.guild.icon.url
                if interaction.guild.icon
                else None
            )
        )

        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(

            embed=embed,

            view=HelpView(),

            ephemeral=False
        )


# =========================================================
# SETUP
# =========================================================

async def setup(bot):

    await bot.add_cog(
        HelpCog(bot)
    )
