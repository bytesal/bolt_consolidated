import os
import discord
from discord import app_commands
from discord.ext import commands

class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Moderation System", description="View all administrative enforcement commands.", emoji="⚠️"),
            discord.SelectOption(label="Support & Modmail", description="View ticketing and communication matrix commands.", emoji="✉️"),
            discord.SelectOption(label="Staff & Quotas", description="View workforce parameters and shift session commands.", emoji="💼"),
            discord.SelectOption(label="System & Utility", description="View core framework deployment and notice commands.", emoji="⚙️")
        ]
        super().__init__(placeholder="Choose an operational sector to view commands...", options=options, custom_id="bolt_help_dropdown_persistent")

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        embed = discord.Embed(color=discord.Color.teal())

        if selection == "Moderation System":
            embed.title = "⚠️ Moderation Infrastructure Manual"
            embed.description = (
                "`/warn` - Issue a formal warning matrix entry onto a target user.\n"
                "`/adwarn` - Issue a specialized warning dealing with promotion protocol violations.\n"
                "`/history` - Query log tracking database for historic records regarding specific targets."
            )
        elif selection == "Support & Modmail":
            embed.title = "✉️ Support Interface Framework"
            embed.description = (
                "`/staffstats` - Retrieve operational performance tracking vectors and resolution metrics.\n"
                "*Note: Support sessions are dynamically handled via direct message transmission routing layers.*"
            )
        elif selection == "Staff & Quotas":
            embed.title = "💼 Workforce Management Console"
            embed.description = (
                "`/setdepartment` - Assign a specific operational department framework onto a staff member.\n"
                "`/removedepartment` - Cleanly remove a target member from specialized department assignments.\n"
                "`/addrank` - Create a system profile reference log for a new structural staff rank.\n"
                "`/addduty` - Link explicit requirement framework updates onto an existing rank configuration.\n"
                "`/poststaffdropdown` - Deploy the structured visual dropdown matrix interface overview.\n"
                "`/deployquotamatrix` - Deploy the interactive button engine terminal dashboard for shifts."
            )
        elif selection == "System & Utility":
            embed.title = "⚙️ Core Utility & Progression Frameworks"
            embed.description = (
                "`/rank` - Evaluate localized structural leveling and progression values metrics.\n"
                "`/sticky` - Affix dynamic notice text block down bottom stream boundary layers.\n"
                "`/unsticky` - Purge notice binding metrics completely from local view matrix.\n"
                "`/setwelcome` - Configure public welcome greetings targeted at a specific text channel.\n"
                "`/setleave` - Configure public departure logs targeted at a specific text channel.\n"
                "`/deployappform` - Stream the recruitment initiation terminal panel into workspaces.\n"
                "`/hrlogs` - Retrieve audit logging metrics synced across application validation tasks.\n"
                "`/sethrchannel` - Configure the primary HR operations target log terminal channel."
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

class HelpDropdownView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HelpDropdown())

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Deploy the primary Bolt interface manual and core operational command directory.")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚡ Bolt All-In-One Mainframe Directory",
            description=(
                "Welcome to the central operations command center for **Bolt**.\n\n"
                "Please utilize the interactive selection matrix menu below to filter through "
                "available command protocols, automation systems, and staff administration panels."
            ),
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url if self.bot.user else None)
        embed.set_footer(text=f"System Core Framework — Authorized Operational Access Only")
        
        await interaction.response.send_message(embed=embed, view=HelpDropdownView(), ephemeral=True)

async def setup(bot):
    # Dynamically remove default help command to prevent duplication conflicts
    if bot.help_command:
        bot.help_command = None
    await bot.add_cog(HelpCog(bot))
