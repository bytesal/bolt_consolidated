import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

# ------------------------------- CATEGORY METADATA -------------------------------

CATEGORY_EMOJIS = {
    "Moderation": "<:mod:133456789012345678>",
    "Ad-Warn": "<:adwarn:133456789012345679>",
    "Modmail": "<:modmail:133456789012345680>",
    "Reception": "<:reception:133456789012345681>",
    "Applications": "<:apps:133456789012345682>",
    "Leveling": "<:leveling:133456789012345683>",
    "Utility": "<:utility:133456789012345684>",
    "Staff": "<:staff:133456789012345685>",
    "Staff Teams": "<:team:133456789012345686>",
    "AutoMod": "<:automod:133456789012345687>",
    "Analytics": "<:analytics:133456789012345688>",
    "Server Linking": "<:link:133456789012345689>",
    "Developer": "<:dev:133456789012345690>"
}
# Fallback to regular emojis if custom ones are not available
DEFAULT_EMOJIS = {
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

COMMANDS_BY_CATEGORY = {
    "Moderation": [
        "`/warn` – Warn a member (expires after set days)",
        "`/removewarn` – Remove a warning by case ID",
        "`/warns` – List active warnings",
        "`/setwarnexpiry` – Set expiry days",
        "`/casenote` – Add private note",
        "`/caseview` – View case details",
        "`/timeout` – Timeout member",
        "`/ban` – Ban member",
        "`/kick` – Kick member",
        "`/history` – View history",
        "`/setmodlog` – Set log channel",
        "`/purge` – Bulk delete",
        "`/purgeuser` – Delete by user"
    ],
    "Ad-Warn": [
        "`/adwarn` – Issue ad warning (counts toward quota)",
        "`/adwarnhistory` – View ad-warn history"
    ],
    "Modmail": [
        "`/setupmodmail` – Configure modmail",
        "`/panel` – Send ticket panel",
        "`DM the bot` – Create ticket",
        "`Claim` – Take ticket",
        "`Unclaim` – Release ticket",
        "`Close` – Close & save transcript"
    ],
    "Reception": [
        "`/setwelcome` – Set welcome message",
        "`/setleave` – Set leave message",
        "`/togglewelcome` – Enable/disable welcome",
        "`/toggleleave` – Enable/disable leave"
    ],
    "Applications": [
        "`/sethrchannel` – Set HR channel",
        "`/deployappform` – Post application form",
        "`/hrlogs` – View HR logs"
    ],
    "Leveling": [
        "`/rank` – View rank",
        "`/leaderboard` – XP leaderboard"
    ],
    "Utility": [
        "`/sticky` – Create sticky message",
        "`/unsticky` – Remove sticky",
        "`/ping` – Bot latency",
        "`/serverinfo` – Server info",
        "`/addreactrole` – Reaction role",
        "`/removereactrole` – Remove reaction role",
        "`/restoreroles` – Restore roles"
    ],
    "Staff": [
        "`/setdepartment` – Assign department",
        "`/removedepartment` – Remove department",
        "`/listdepartments` – List assignments",
        "`/addrank` – Create staff rank",
        "`/addduty` – Add rank duty",
        "`/poststaffdropdown` – Show ranks",
        "`/deployquotamatrix` – Quota dashboard",
        "`/setauditchannel` – Set audit channel",
        "`/auditlog` – View audit log"
    ],
    "Staff Teams": [
        "`/createteam` – Create team",
        "`/addmember` – Add member",
        "`/removemember` – Remove member",
        "`/addresponsibility` – Add duty",
        "`/poststaffpanel` – Show team panel"
    ],
    "AutoMod": [
        "`!automod links true/false` – Toggle anti‑links",
        "`!automod spam true/false` – Toggle punishment spam",
        "`!automod mentions true/false` – Mention protection",
        "`!automod slowmode true/false` – Toggle auto‑slowmode",
        "`!allowads` – Allow ads in channel",
        "`!removeads` – Disallow ads"
    ],
    "Analytics": [
        "`/dashboard` – Bot analytics",
        "`/botstats` – Detailed stats"
    ],
    "Server Linking": [
        "`/linkserver` – Link staff and public guilds",
        "`/setmainserver` – Set main server",
        "`/setstaffserver` – Set staff server",
        "`/viewconfig` – View config",
        "`/resetconfig` – Reset config"
    ],
    "Developer": [
        "`/sync` – Sync commands",
        "`/reload` – Reload cog",
        "`/load` – Load cog",
        "`/unload` – Unload cog",
        "`/shutdown` – Shut down",
        "`/restart` – Restart",
        "`/eval` – Execute code",
        "`/devpanel` – Dev panel",
        "`/blacklistuser` – Global user blacklist",
        "`/unblacklistuser` – Remove user blacklist",
        "`/blacklistguild` – Global guild blacklist",
        "`/unblacklistguild` – Remove guild blacklist"
    ]
}

# ------------------------------- DROPDOWN -------------------------------
class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = []
        for category in COMMANDS_BY_CATEGORY.keys():
            emoji = DEFAULT_EMOJIS.get(category, "📌")
            options.append(
                discord.SelectOption(
                    label=category,
                    emoji=emoji,
                    description=f"View {category.lower()} commands",
                    value=category
                )
            )
        super().__init__(
            placeholder="📂 Select a category",
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
        emoji = DEFAULT_EMOJIS.get(category, "📌")
        commands_list = COMMANDS_BY_CATEGORY.get(category, ["No commands available."])
        embed = discord.Embed(
            title=f"{emoji}  {category} Commands",
            description=f"Here are all the **{category.lower()}** commands available in Bolt Engine.\n\u200b",
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )
        # Split commands into chunks of 10 to avoid field limits
        chunks = [commands_list[i:i+10] for i in range(0, len(commands_list), 10)]
        for i, chunk in enumerate(chunks):
            embed.add_field(
                name="Commands" if len(chunks) == 1 else f"Commands (Part {i+1})",
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


# ------------------------------- MAIN COG -------------------------------
class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="View all available bot commands.")
    async def help_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = self._build_main_embed(interaction)
        await interaction.followup.send(embed=embed, view=HelpView(), ephemeral=False)

    def _build_main_embed(self, interaction: discord.Interaction) -> discord.Embed:
        # Create a clean, modern main embed
        embed = discord.Embed(
            title="⚙️ **Bolt Engine Help Center**",
            description=(
                "Welcome to the interactive help system.\n"
                "Select a category from the dropdown below to explore commands.\n"
                "\u200b"
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )
        # Categories as a clean inline field (4 per row emojis)
        categories_text = ""
        for cat in COMMANDS_BY_CATEGORY.keys():
            emoji = DEFAULT_EMOJIS.get(cat, "📌")
            categories_text += f"{emoji} **{cat}**\n"
        embed.add_field(name="📚 **Categories**", value=categories_text, inline=True)

        # Key features inline
        features = (
            "• Cross‑Server Moderation\n"
            "• Ad‑Warn Quota System\n"
            "• Professional Modmail\n"
            "• Persistent Views\n"
            "• Role Persistence\n"
            "• Advanced AutoMod & Slowmode\n"
            "• Staff Quotas & Departments"
        )
        embed.add_field(name="✨ **Key Features**", value=features, inline=True)

        # Tip or info field
        embed.add_field(
            name="💡 **Tip**",
            value="Use `/sync` to update slash commands after bot updates.\nNeed help? Join our [Support Server](https://discord.gg/invite) (replace with actual invite).",
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
