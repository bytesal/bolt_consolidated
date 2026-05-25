import discord
from discord.ext import commands
from discord import app_commands


class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Moderation", emoji="🛡️", description="Moderation and punishment commands."),
            discord.SelectOption(label="Ad-Warn", emoji="⚠️", description="Advertising warning system & quota tracking."),
            discord.SelectOption(label="Modmail", emoji="📩", description="Support and ticket system commands."),
            discord.SelectOption(label="Reception", emoji="🎉", description="Welcome, leave, and onboarding systems."),
            discord.SelectOption(label="Applications", emoji="📄", description="Applications and recruitment system."),
            discord.SelectOption(label="Leveling", emoji="📈", description="XP and leveling commands."),
            discord.SelectOption(label="Utility", emoji="⚙️", description="Utility and management commands."),
            discord.SelectOption(label="Staff", emoji="👥", description="Staff department and quota commands."),
            discord.SelectOption(label="Staff Teams", emoji="📂", description="Dynamic staff department system."),
            discord.SelectOption(label="AutoMod", emoji="🤖", description="Automatic moderation system."),
            discord.SelectOption(label="Analytics", emoji="📊", description="Statistics and analytics commands."),
            discord.SelectOption(label="Server Linking", emoji="🔗", description="Cross-server management commands."),
            discord.SelectOption(label="Developer", emoji="🧑‍💻", description="Developer-only commands."),
        ]
        super().__init__(placeholder="Select a command category...", min_values=1, max_values=1,
                         options=options, custom_id="help_menu_dropdown")

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        embed = discord.Embed(color=discord.Color.blurple())

        if category == "Moderation":
            embed.title = "🛡️ Moderation Commands"
            embed.description = "Cross-server moderation commands used by staff members."
            embed.add_field(name="Available Commands", value="\n".join([
                "`/warn` → Warn a member.",
                "`/removewarn` → Remove a specific warning by case ID.",
                "`/warns` → List active warnings for a user.",
                "`/timeout` → Timeout a member.",
                "`/kick` → Kick a member.",
                "`/ban` → Ban a member.",
                "`/history` → View moderation history.",
                "`/setmodlog` → Configure moderation logs.",
                "`/purge` → Delete messages.",
                "`/purgeuser` → Delete messages from a user.",
            ]), inline=False)

        elif category == "Ad-Warn":
            embed.title = "⚠️ Ad‑Warn System"
            embed.description = "Issue advertising warnings and track weekly staff quotas."
            embed.add_field(name="Available Commands", value="\n".join([
                "`/adwarn` → Issue an advertising warning (counts toward weekly quota).",
                "`/adwarnhistory` → View ad‑warn history for a user.",
            ]), inline=False)

        elif category == "Modmail":
            embed.title = "📩 Modmail Commands"
            embed.description = "Professional support ticket system with anonymous replies and transcripts."
            embed.add_field(name="Available Commands", value="\n".join([
                "`/setupmodmail` → Configure modmail category and transcript channel.",
                "`/panel` → Send modmail panel.",
                "`DM the bot` → Create a support ticket.",
                "`Claim Button` → Claim a ticket.",
                "`Close Button` → Close a ticket (saves transcript).",
            ]), inline=False)

        elif category == "Reception":
            embed.title = "🎉 Reception Commands"
            embed.description = "Welcome, leave, and onboarding systems."
            embed.add_field(name="Available Commands", value="\n".join([
                "`/setwelcome` → Configure welcome messages.",
                "`/setleave` → Configure leave messages.",
                "`/togglewelcome` → Enable or disable welcome messages.",
                "`/toggleleave` → Enable or disable leave messages.",
                "`/setautorole` → Configure autoroles.",
                "`/setruleschannel` → Configure rules channel.",
            ]), inline=False)

        elif category == "Applications":
            embed.title = "📄 Application Commands"
            embed.description = "Applications and recruitment system."
            embed.add_field(name="Available Commands", value="\n".join([
                "`/sethrchannel` → Set HR log channel.",
                "`/deployappform` → Deploy application form.",
                "`/hrlogs` → View HR decision logs.",
            ]), inline=False)

        elif category == "Leveling":
            embed.title = "📈 Leveling Commands"
            embed.description = "XP and ranking system commands."
            embed.add_field(name="Available Commands", value="\n".join([
                "`/rank` → View user rank.",
                "`/leaderboard` → View XP leaderboard.",
                "`/setlevelchannel` → Configure level‑up channel.",
                "`/setxprate` → Configure XP gain rate.",
            ]), inline=False)

        elif category == "Utility":
            embed.title = "⚙️ Utility Commands"
            embed.description = "General utility and management commands."
            embed.add_field(name="Available Commands", value="\n".join([
                "`/sticky` → Create sticky messages.",
                "`/unsticky` → Remove sticky messages.",
                "`/ping` → View bot latency.",
                "`/serverinfo` → View server information.",
                "`/addreactrole` → Add a reaction role to a message.",
                "`/removereactrole` → Remove a reaction role.",
            ]), inline=False)

        elif category == "Staff":
            embed.title = "👥 Staff Commands"
            embed.description = "Department assignment, quota tracking, and audit logs."
            embed.add_field(name="Available Commands", value="\n".join([
                "`/setdepartment` → Assign a staff member to a department.",
                "`/removedepartment` → Remove a staff member from their department.",
                "`/listdepartments` → List all staff members and their departments.",
                "`/addrank` → Create a staff rank.",
                "`/addduty` → Add duties to a rank.",
                "`/poststaffdropdown` → Post the ranks dropdown.",
                "`/deployquotamatrix` → Deploy shift/quota dashboard.",
                "`/setauditchannel` → Set the channel for audit log notifications.",
                "`/auditlog` → View recent audit log entries.",
            ]), inline=False)

        elif category == "Staff Teams":
            embed.title = "📂 Staff Team Commands"
            embed.description = "Dynamic staff department system."
            embed.add_field(name="Available Commands", value="\n".join([
                "`/createteam` → Create a staff team.",
                "`/addmember` → Add a member to a team.",
                "`/removemember` → Remove a member from a team.",
                "`/addresponsibility` → Add responsibilities to a team.",
                "`/poststaffpanel` → Deploy the public staff panel.",
            ]), inline=False)

        elif category == "AutoMod":
            embed.title = "🤖 AutoMod Commands"
            embed.description = "Automatic moderation configuration, including slowmode on spam."
            embed.add_field(name="Available Commands", value="\n".join([
                "`!automod links true/false` → Toggle anti‑links.",
                "`!automod spam true/false` → Toggle anti‑spam (punishment).",
                "`!automod mentions true/false` → Toggle mention protection.",
                "`!automod slowmode true/false` → Toggle auto‑slowmode on spam.",
                "`!allowads` → Allow advertisements in channel.",
                "`!removeads` → Remove advertisement permissions.",
            ]), inline=False)

        elif category == "Analytics":
            embed.title = "📊 Analytics Commands"
            embed.description = "Bot statistics and analytics."
            embed.add_field(name="Available Commands", value="\n".join([
                "`/dashboard` → View analytics dashboard.",
                "`/botstats` → View detailed bot statistics.",
            ]), inline=False)

        elif category == "Server Linking":
            embed.title = "🔗 Server Linking Commands"
            embed.description = "Cross‑server infrastructure management."
            embed.add_field(name="Available Commands", value="\n".join([
                "`/linkserver` → Link staff and public servers.",
                "`/setmainserver` → Set main community server.",
                "`/setstaffserver` → Set staff control server.",
                "`/viewconfig` → View current configuration.",
                "`/resetconfig` → Reset bot configuration.",
            ]), inline=False)

        elif category == "Developer":
            if interaction.user.id not in interaction.client.DEVELOPER_IDS:
                embed.title = "🔒 Restricted Category"
                embed.description = "You do not have permission to access developer commands."
                embed.color = discord.Color.red()
                embed.set_footer(text="Developer Access Required")
                return await interaction.response.edit_message(embed=embed, view=self.view)

            embed.title = "🧑‍💻 Developer Commands"
            embed.description = "Developer‑only management commands."
            embed.add_field(name="Available Commands", value="\n".join([
                "`/sync` → Sync application commands.",
                "`/reload` → Reload a cog.",
                "`/load` → Load a cog.",
                "`/unload` → Unload a cog.",
                "`/shutdown` → Shutdown the bot.",
                "`/restart` → Restart the bot (Railway‑safe).",
                "`/eval` → Execute Python code.",
                "`/devpanel` → Open developer panel.",
                "`/blacklistuser` → Blacklist a user globally.",
                "`/unblacklistuser` → Remove user blacklist.",
                "`/blacklistguild` → Blacklist a guild globally.",
                "`/unblacklistguild` → Remove guild blacklist.",
            ]), inline=False)

        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HelpDropdown())


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="View all available bot commands.")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 Bolt Engine Help Center",
            description="Welcome to the interactive help system.\n\nUse the dropdown menu below to browse all command categories.",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="📚 Command Categories",
            value=(
                "🛡️ Moderation\n"
                "⚠️ Ad‑Warn\n"
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
                "• Cross‑Server Moderation\n"
                "• Ad‑Warn Quota System\n"
                "• Persistent Systems\n"
                "• Professional Modmail\n"
                "• Dynamic Staff Teams\n"
                "• Advanced AutoMod"
            ),
            inline=False
        )
        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text=interaction.guild.name if interaction.guild else "Bolt Engine",
                         icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=False)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
