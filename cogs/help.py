import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

# Emoji constants for categories
CATEGORY_EMOJIS = {
    "Moderation": "🛡️",
    "Ad-Warn": "⚠️",
    "Modmail": "📩",
    "Reception": "🎉",
    "Applications": "📄",
    "Leveling": "📈",
    "Utility": "⚙️",
    "Staff": "👥",
    "Staff Teams": "📂",
    "AutoMod": "🤖",
    "Analytics": "📊",
    "Server Linking": "🔗",
    "Developer": "🧑‍💻"
}

# Command lists (keep these up to date)
COMMANDS_BY_CATEGORY = {
    "Moderation": [
        "`/warn` – Warn a member (expires after set days)",
        "`/removewarn` – Remove a specific warning by case ID",
        "`/warns` – List active warnings for a user",
        "`/setwarnexpiry` – Set days until warnings expire",
        "`/casenote` – Add a private note to a case",
        "`/caseview` – View a case with all notes",
        "`/timeout` – Timeout a member",
        "`/ban` – Ban a member",
        "`/kick` – Kick a member",
        "`/history` – View moderation history",
        "`/setmodlog` – Configure moderation logs",
        "`/purge` – Delete messages",
        "`/purgeuser` – Delete messages from a user"
    ],
    "Ad-Warn": [
        "`/adwarn` – Issue an advertising warning (counts toward weekly quota)",
        "`/adwarnhistory` – View ad‑warn history for a user"
    ],
    "Modmail": [
        "`/setupmodmail` – Configure modmail category and transcript channel",
        "`/panel` – Send modmail panel",
        "`DM the bot` – Create a support ticket",
        "`Claim Button` – Claim a ticket (prevents others from replying)",
        "`Unclaim Button` – Release a claimed ticket",
        "`Close Button` – Close a ticket (saves transcript)"
    ],
    "Reception": [
        "`/setwelcome` – Configure welcome messages",
        "`/setleave` – Configure leave messages",
        "`/togglewelcome` – Enable or disable welcome messages",
        "`/toggleleave` – Enable or disable leave messages"
    ],
    "Applications": [
        "`/sethrchannel` – Set HR log channel",
        "`/deployappform` – Deploy application form",
        "`/hrlogs` – View HR decision logs"
    ],
    "Leveling": [
        "`/rank` – View user rank",
        "`/leaderboard` – View XP leaderboard"
    ],
    "Utility": [
        "`/sticky` – Create sticky messages",
        "`/unsticky` – Remove sticky messages",
        "`/ping` – View bot latency",
        "`/serverinfo` – View server information",
        "`/addreactrole` – Add a reaction role to a message",
        "`/removereactrole` – Remove a reaction role",
        "`/restoreroles` – Manually restore roles from backup"
    ],
    "Staff": [
        "`/setdepartment` – Assign a staff member to a department",
        "`/removedepartment` – Remove a staff member from their department",
        "`/listdepartments` – List all staff members and their departments",
        "`/addrank` – Create a staff rank",
        "`/addduty` – Add duties to a rank",
        "`/poststaffdropdown` – Post the ranks dropdown",
        "`/deployquotamatrix` – Deploy shift/quota dashboard",
        "`/setauditchannel` – Set the channel for audit log notifications",
        "`/auditlog` – View recent audit log entries"
    ],
    "Staff Teams": [
        "`/createteam` – Create a staff team",
        "`/addmember` – Add a member to a team",
        "`/removemember` – Remove a member from a team",
        "`/addresponsibility` – Add responsibilities to a team",
        "`/poststaffpanel` – Deploy the public staff panel"
    ],
    "AutoMod": [
        "`!automod links true/false` – Toggle anti‑links",
        "`!automod spam true/false` – Toggle anti‑spam (punishment)",
        "`!automod mentions true/false` – Toggle mention protection",
        "`!automod slowmode true/false` – Toggle auto‑slowmode on spam",
        "`!allowads` – Allow advertisements in channel",
        "`!removeads` – Remove advertisement permissions"
    ],
    "Analytics": [
        "`/dashboard` – View analytics dashboard",
        "`/botstats` – View detailed bot statistics"
    ],
    "Server Linking": [
        "`/linkserver` – Link staff and public servers",
        "`/setmainserver` – Set main community server",
        "`/setstaffserver` – Set staff control server",
        "`/viewconfig` – View current configuration",
        "`/resetconfig` – Reset bot configuration"
    ],
    "Developer": [
        "`/sync` – Sync application commands",
        "`/reload` – Reload a cog",
        "`/load` – Load a cog",
        "`/unload` – Unload a cog",
        "`/shutdown` – Shutdown the bot",
        "`/restart` – Restart the bot (Railway‑safe)",
        "`/eval` – Execute Python code",
        "`/devpanel` – Open developer panel",
        "`/blacklistuser` – Blacklist a user globally",
        "`/unblacklistuser` – Remove user blacklist",
        "`/blacklistguild` – Blacklist a guild globally",
        "`/unblacklistguild` – Remove guild blacklist"
    ]
}


class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = []
        for category in COMMANDS_BY_CATEGORY.keys():
            emoji = CATEGORY_EMOJIS.get(category, "📌")
            options.append(
                discord.SelectOption(
                    label=category,
                    emoji=emoji,
                    description=f"View {category.lower()} commands",
                    value=category
                )
            )
        super().__init__(
            placeholder="📂 Select a command category...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="help_category_dropdown_persistent"
        )

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        embed = self._build_category_embed(interaction, category)
        await interaction.response.edit_message(embed=embed, view=self.view)

    def _build_category_embed(self, interaction: discord.Interaction, category: str) -> discord.Embed:
        emoji = CATEGORY_EMOJIS.get(category, "📌")
        commands_list = COMMANDS_BY_CATEGORY.get(category, ["No commands available."])
        embed = discord.Embed(
            title=f"{emoji} {category} Commands",
            description=f"Here are all the {category.lower()} commands available in Bolt Engine.",
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )
        # Split commands into chunks of 10 to avoid field limits
        chunks = [commands_list[i:i+10] for i in range(0, len(commands_list), 10)]
        for i, chunk in enumerate(chunks):
            embed.add_field(
                name=f"📖 Command Group {i+1}" if len(chunks) > 1 else "Available Commands",
                value="\n".join(chunk),
                inline=False
            )
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name} • Bolt Engine",
            icon_url=interaction.user.display_avatar.url
        )
        embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
        return embed


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HelpDropdown())


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="View all available bot commands.")
    async def help_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = self._build_main_embed(interaction)
        await interaction.followup.send(embed=embed, view=HelpView(), ephemeral=False)

    def _build_main_embed(self, interaction: discord.Interaction) -> discord.Embed:
        embed = discord.Embed(
            title="🤖 Bolt Engine Help Center",
            description=(
                "Welcome to the interactive help system.\n\n"
                "Use the dropdown menu below to browse all command categories.\n"
                "Each category contains detailed information about available commands."
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )
        # Add a summary field
        categories_list = "\n".join([f"{CATEGORY_EMOJIS.get(cat, '📌')} **{cat}**" for cat in COMMANDS_BY_CATEGORY.keys()])
        embed.add_field(
            name="📚 Command Categories",
            value=categories_list,
            inline=False
        )
        embed.add_field(
            name="✨ Key Features",
            value=(
                "• Cross‑Server Moderation\n"
                "• Ad‑Warn Quota System\n"
                "• Professional Modmail with Transcripts\n"
                "• Persistent Views & Role Persistence\n"
                "• Advanced AutoMod & Slowmode\n"
                "• Staff Quotas & Department Management"
            ),
            inline=False
        )
        embed.set_thumbnail(url=interaction.client.user.display_avatar.url)
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name} • Bolt Engine v5.0",
            icon_url=interaction.user.display_avatar.url
        )
        return embed


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
