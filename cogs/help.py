import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

# ------------------------------- CATEGORY DATA -------------------------------
CATEGORIES = {
    "mod": {
        "name": "Moderation",
        "emoji": "🛡️",
        "color": discord.Color.red(),
        "commands": [
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
        ]
    },
    "adwarn": {
        "name": "Ad‑Warn",
        "emoji": "⚠️",
        "color": discord.Color.orange(),
        "commands": [
            "`/adwarn` – Issue ad warning (counts toward quota)",
            "`/adwarnhistory` – View ad‑warn history"
        ]
    },
    "modmail": {
        "name": "Modmail",
        "emoji": "📩",
        "color": discord.Color.gold(),
        "commands": [
            "`/setupmodmail` – Configure modmail",
            "`/panel` – Send ticket panel",
            "`DM the bot` – Create ticket",
            "`Claim` – Take ticket",
            "`Unclaim` – Release ticket",
            "`Close` – Close & save transcript"
        ]
    },
    "reception": {
        "name": "Reception",
        "emoji": "🎉",
        "color": discord.Color.teal(),
        "commands": [
            "`/setwelcome` – Set welcome message",
            "`/setleave` – Set leave message",
            "`/togglewelcome` – Enable/disable welcome",
            "`/toggleleave` – Enable/disable leave"
        ]
    },
    "apps": {
        "name": "Applications",
        "emoji": "📄",
        "color": discord.Color.purple(),
        "commands": [
            "`/sethrchannel` – Set HR channel",
            "`/deployappform` – Post application form",
            "`/hrlogs` – View HR logs"
        ]
    },
    "leveling": {
        "name": "Leveling",
        "emoji": "📈",
        "color": discord.Color.green(),
        "commands": [
            "`/rank` – View rank",
            "`/leaderboard` – XP leaderboard"
        ]
    },
    "utility": {
        "name": "Utility",
        "emoji": "⚙️",
        "color": discord.Color.light_gray(),
        "commands": [
            "`/sticky` – Create sticky message",
            "`/unsticky` – Remove sticky",
            "`/ping` – Bot latency",
            "`/serverinfo` – Server info",
            "`/addreactrole` – Reaction role",
            "`/removereactrole` – Remove reaction role",
            "`/restoreroles` – Restore roles"
        ]
    },
    "staff": {
        "name": "Staff Management",
        "emoji": "👥",
        "color": discord.Color.dark_blue(),
        "commands": [
            "`/setdepartment` – Assign department",
            "`/removedepartment` – Remove department",
            "`/listdepartments` – List assignments",
            "`/addrank` – Create staff rank",
            "`/addduty` – Add rank duty",
            "`/poststaffdropdown` – Show ranks",
            "`/deployquotamatrix` – Quota dashboard",
            "`/setauditchannel` – Set audit channel",
            "`/auditlog` – View audit log"
        ]
    },
    "teams": {
        "name": "Staff Teams",
        "emoji": "📂",
        "color": discord.Color.dark_purple(),
        "commands": [
            "`/createteam` – Create team",
            "`/addmember` – Add member",
            "`/removemember` – Remove member",
            "`/addresponsibility` – Add duty",
            "`/poststaffpanel` – Show team panel"
        ]
    },
    "automod": {
        "name": "AutoMod",
        "emoji": "🤖",
        "color": discord.Color.dark_gray(),
        "commands": [
            "`!automod links true/false` – Toggle anti‑links",
            "`!automod spam true/false` – Toggle punishment spam",
            "`!automod mentions true/false` – Mention protection",
            "`!automod slowmode true/false` – Toggle auto‑slowmode",
            "`!allowads` – Allow ads in channel",
            "`!removeads` – Disallow ads"
        ]
    },
    "analytics": {
        "name": "Analytics",
        "emoji": "📊",
        "color": discord.Color.dark_teal(),
        "commands": [
            "`/dashboard` – Bot analytics",
            "`/botstats` – Detailed stats"
        ]
    },
    "link": {
        "name": "Server Linking",
        "emoji": "🔗",
        "color": discord.Color.blue(),
        "commands": [
            "`/linkserver` – Link staff and public guilds",
            "`/setmainserver` – Set main server",
            "`/setstaffserver` – Set staff server",
            "`/viewconfig` – View config",
            "`/resetconfig` – Reset config"
        ]
    },
    "dev": {
        "name": "Developer",
        "emoji": "🧑‍💻",
        "color": discord.Color.dark_gold(),
        "commands": [
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
}

# Order of buttons (first row, second row, etc.)
BUTTON_ROWS = [
    ["mod", "adwarn", "modmail", "reception", "apps"],
    ["leveling", "utility", "staff", "teams", "automod"],
    ["analytics", "link", "dev"]
]


# ------------------------------- HELP VIEW WITH BUTTONS -------------------------------
class HelpView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=None)
        self.interaction = interaction
        self.current_category = None
        self._build_buttons()

    def _build_buttons(self):
        """Create category buttons in rows."""
        for row_buttons in BUTTON_ROWS:
            row = []
            for key in row_buttons:
                cat = CATEGORIES[key]
                button = discord.ui.Button(
                    label=cat["name"],
                    emoji=cat["emoji"],
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"help_{key}"
                )
                button.callback = self.make_callback(key)
                row.append(button)
            # Add each button individually (they will auto-arrange into rows)
            for btn in row:
                self.add_item(btn)

        # Add a "Home" button at the bottom
        home_button = discord.ui.Button(
            label="Home",
            emoji="🏠",
            style=discord.ButtonStyle.primary,
            custom_id="help_home"
        )
        home_button.callback = self.home_callback
        self.add_item(home_button)

    def make_callback(self, category_key):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.interaction.user.id:
                await interaction.response.send_message("This help menu is not for you.", ephemeral=True)
                return
            self.current_category = category_key
            embed = self._build_category_embed(category_key)
            await interaction.response.edit_message(embed=embed, view=self)
        return callback

    async def home_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("This help menu is not for you.", ephemeral=True)
            return
        self.current_category = None
        embed = self._build_main_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    def _build_main_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="⚙️ Bolt Engine Help Center",
            description=(
                "Welcome to the **interactive help system**.\n"
                "Select a category below to view all commands.\n\n"
                "💡 *Buttons are persistent – they survive bot restarts.*"
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )
        # List all categories in a clean field
        categories_list = "\n".join(
            f"{cat['emoji']} **{cat['name']}**"
            for cat in CATEGORIES.values()
        )
        embed.add_field(name="📚 **Categories**", value=categories_list, inline=True)

        # Feature highlights
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

        embed.set_thumbnail(url=self.interaction.client.user.display_avatar.url)
        embed.set_footer(
            text=f"Requested by {self.interaction.user.display_name} • Bolt Engine v5.0",
            icon_url=self.interaction.user.display_avatar.url
        )
        return embed

    def _build_category_embed(self, category_key: str) -> discord.Embed:
        cat = CATEGORIES[category_key]
        embed = discord.Embed(
            title=f"{cat['emoji']}  {cat['name']} Commands",
            description=f"Here are all the **{cat['name'].lower()}** commands available in Bolt Engine.",
            color=cat["color"],
            timestamp=datetime.utcnow()
        )
        # Split commands into chunks of 10 to avoid field limits
        commands_list = cat["commands"]
        chunks = [commands_list[i:i+10] for i in range(0, len(commands_list), 10)]
        for i, chunk in enumerate(chunks):
            embed.add_field(
                name="Commands" if len(chunks) == 1 else f"Commands (Part {i+1})",
                value="\n".join(chunk),
                inline=False
            )
        embed.set_footer(
            text=f"Category: {cat['name']} • Page {1 if len(chunks)==1 else f'1/{len(chunks)}'} • Bolt Engine",
            icon_url=self.interaction.client.user.display_avatar.url
        )
        embed.set_thumbnail(url=self.interaction.client.user.display_avatar.url)
        return embed


# ------------------------------- HELP COG -------------------------------
class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="View all available bot commands.")
    async def help_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = HelpView(interaction)
        embed = view._build_main_embed()
        await interaction.followup.send(embed=embed, view=view, ephemeral=False)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
