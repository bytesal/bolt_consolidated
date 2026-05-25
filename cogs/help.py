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
        # Already editing the original message, no defer needed
        category = self.values[0]
        embed = discord.Embed(color=discord.Color.blurple())
        # ... (rest of the embed building code unchanged from Phase 4/5)
        # For brevity, keep your existing embed building logic.
        # Ensure the last line is:
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
        # Defer to prevent timeout (safe practice)
        await interaction.response.defer()
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
        await interaction.followup.send(embed=embed, view=HelpView(), ephemeral=False)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
