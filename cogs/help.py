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
                description="View moderation commands."
            ),

            discord.SelectOption(
                label="Modmail",
                emoji="📩",
                description="View modmail commands."
            ),

            discord.SelectOption(
                label="Reception",
                emoji="🎉",
                description="View reception system commands."
            ),

            discord.SelectOption(
                label="Applications",
                emoji="📄",
                description="View application system commands."
            ),

            discord.SelectOption(
                label="Leveling",
                emoji="📈",
                description="View leveling commands."
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

            discord.SelectOption(
                label="AutoMod",
                emoji="🤖",
                description="View automod commands."
            ),

            discord.SelectOption(
                label="Analytics",
                emoji="📊",
                description="View analytics commands."
            ),

            discord.SelectOption(
                label="Developer",
                emoji="🧑‍💻",
                description="View developer commands."
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

                "`/setupmodmail` → Setup modmail category.",
                "`/panel` → Send modmail panel.",
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
        # RECEPTION
        # =====================================================

        elif category == "Reception":

            embed.title = "🎉 Reception Commands"

            embed.description = (
                "Reception and welcome system commands."
            )

            commands_list = [

                "`/setwelcome` → Configure welcome messages.",
                "`/setleave` → Configure leave messages.",
                "`/setautorole` → Configure autoroles.",
                "`/setruleschannel` → Configure rules channel.",
            ]

            embed.add_field(
                name="Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # APPLICATIONS
        # =====================================================

        elif category == "Applications":

            embed.title = "📄 Application Commands"

            embed.description = (
                "Staff applications and forms system."
            )

            commands_list = [

                "`/applicationpanel` → Send application panel.",
                "`/createapplication` → Create an application.",
                "`/applications` → View applications.",
                "`/acceptapplication` → Accept an application.",
                "`/denyapplication` → Deny an application.",
            ]

            embed.add_field(
                name="Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # LEVELING
        # =====================================================

        elif category == "Leveling":

            embed.title = "📈 Leveling Commands"

            embed.description = (
                "XP and leveling system commands."
            )

            commands_list = [

                "`/rank` → View your rank.",
                "`/leaderboard` → View XP leaderboard.",
                "`/setlevelchannel` → Configure level-up channel.",
                "`/setxprate` → Configure XP gain rate.",
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
                "General utility commands."
            )

            commands_list = [

                "`/sticky` → Create sticky messages.",
                "`/unsticky` → Remove sticky messages.",
                "`/ping` → View bot latency.",
                "`/serverinfo` → View server information.",
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

        # =====================================================
        # AUTOMOD
        # =====================================================

        elif category == "AutoMod":

            embed.title = "🤖 AutoMod Commands"

            embed.description = (
                "Advanced automatic moderation system."
            )

            commands_list = [

                "`!automod links true/false` → Enable or disable anti-links.",

                "`!automod spam true/false` → Enable or disable anti-spam.",

                "`!automod mentions true/false` → Enable or disable anti-mention spam.",

                "`!automod allowads` → Allow advertisements in current channel.",

                "`!automod removeads` → Remove advertisements from current channel."
            ]

            embed.add_field(
                name="Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # ANALYTICS
        # =====================================================

        elif category == "Analytics":

            embed.title = "📊 Analytics Commands"

            embed.description = (
                "Bot analytics and statistics."
            )

            commands_list = [

                "`/dashboard` → View analytics dashboard.",

                "`/botstats` → View detailed bot stats."
            ]

            embed.add_field(
                name="Commands",
                value="\n".join(commands_list),
                inline=False
            )

        # =====================================================
        # DEVELOPER
        # =====================================================

        elif category == "Developer":

            embed.title = "🧑‍💻 Developer Commands"

            embed.description = (
                "Developer-only management commands."
            )

            commands_list = [

                "`/devpanel` → Open developer panel.",

                "`/blacklistuser` → Blacklist a user globally.",

                "`/unblacklistuser` → Remove user blacklist.",

                "`/blacklistguild` → Blacklist a guild globally.",

                "`/unblacklistguild` → Remove guild blacklist."
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


# =========================================================
# HELP VIEW
# =========================================================

class HelpView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(HelpDropdown())


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
                "🎉 Reception\n"
                "📄 Applications\n"
                "📈 Leveling\n"
                "⚙️ Utility\n"
                "👥 Staff\n"
                "🤖 AutoMod\n"
                "📊 Analytics\n"
                "🧑‍💻 Developer"

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
