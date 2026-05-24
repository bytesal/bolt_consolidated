import discord
from discord.ext import commands
from discord import app_commands
import os


# =========================================================
# DEV PANEL VIEW
# =========================================================

class DeveloperPanelView(
    discord.ui.View
):

    def __init__(
        self,
        bot
    ):

        super().__init__(
            timeout=None
        )

        self.bot = bot

    # =====================================================
    # CHECK
    # =====================================================

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ):

        if (
            interaction.user.id
            not in self.bot.DEVELOPER_IDS
        ):

            await interaction.response.send_message(
                "❌ Developer only.",
                ephemeral=True
            )

            return False

        return True

    # =====================================================
    # SYNC
    # =====================================================

    @discord.ui.button(
        label="Sync",
        style=discord.ButtonStyle.green,
        emoji="🔄",
        custom_id="devpanel_sync"
    )
    async def sync_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        synced = await self.bot.tree.sync()

        await interaction.response.send_message(

            f"✅ Synced "
            f"{len(synced)} commands.",

            ephemeral=True
        )

    # =====================================================
    # RELOAD
    # =====================================================

    @discord.ui.button(
        label="Reload",
        style=discord.ButtonStyle.blurple,
        emoji="♻️",
        custom_id="devpanel_reload"
    )
    async def reload_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        loaded = []
        failed = []

        for filename in os.listdir("cogs"):

            if (
                filename.endswith(".py")
                and not filename.startswith("__")
            ):

                cog = f"cogs.{filename[:-3]}"

                try:

                    await self.bot.reload_extension(
                        cog
                    )

                    loaded.append(
                        cog
                    )

                except Exception as e:

                    failed.append(
                        f"{cog}: {e}"
                    )

        embed = discord.Embed(

            title="♻️ Reload Results",

            color=discord.Color.orange()
        )

        embed.add_field(

            name="✅ Reloaded",

            value="\n".join(loaded)
            if loaded
            else "None",

            inline=False
        )

        embed.add_field(

            name="❌ Failed",

            value="\n".join(failed)
            if failed
            else "None",

            inline=False
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # =====================================================
    # BOT STATS
    # =====================================================

    @discord.ui.button(
        label="Stats",
        style=discord.ButtonStyle.gray,
        emoji="📊",
        custom_id="devpanel_stats"
    )
    async def stats_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        embed = discord.Embed(

            title="📊 Developer Stats",

            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Servers",
            value=str(len(self.bot.guilds))
        )

        embed.add_field(
            name="Users",
            value=str(

                sum(
                    guild.member_count
                    for guild
                    in self.bot.guilds
                )
            )
        )

        embed.add_field(
            name="Commands",
            value=str(
                len(
                    self.bot.tree.get_commands()
                )
            )
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    # =====================================================
    # PING
    # =====================================================

    @discord.ui.button(
        label="Ping",
        style=discord.ButtonStyle.green,
        emoji="⚡",
        custom_id="devpanel_ping"
    )
    async def ping_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        latency = round(
            self.bot.latency * 1000
        )

        await interaction.response.send_message(

            f"⚡ Pong: "
            f"`{latency}ms`",

            ephemeral=True
        )

    # =====================================================
    # SHUTDOWN
    # =====================================================

    @discord.ui.button(
        label="Shutdown",
        style=discord.ButtonStyle.red,
        emoji="🛑",
        custom_id="devpanel_shutdown"
    )
    async def shutdown_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_message(

            "🛑 Shutting down...",

            ephemeral=True
        )

        await self.bot.close()


# =========================================================
# COG
# =========================================================

class DeveloperPanelCog(commands.Cog):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

    # =====================================================
    # PANEL COMMAND
    # =====================================================

    @app_commands.command(
        name="devpanel",
        description="Open developer panel."
    )
    async def devpanel(
        self,
        interaction: discord.Interaction
    ):

        if (
            interaction.user.id
            not in self.bot.DEVELOPER_IDS
        ):

            return await interaction.response.send_message(
                "❌ Developer only.",
                ephemeral=True
            )

        embed = discord.Embed(

            title="🧑‍💻 Developer Panel",

            description=(
                "Advanced developer controls "
                "for Bolt Engine."
            ),

            color=discord.Color.dark_gold()
        )

        embed.add_field(
            name="🔄 Sync",
            value="Sync slash commands.",
            inline=False
        )

        embed.add_field(
            name="♻️ Reload",
            value="Reload all cogs.",
            inline=False
        )

        embed.add_field(
            name="📊 Stats",
            value="View live statistics.",
            inline=False
        )

        embed.add_field(
            name="⚡ Ping",
            value="View bot latency.",
            inline=False
        )

        embed.add_field(
            name="🛑 Shutdown",
            value="Shutdown the bot.",
            inline=False
        )

        await interaction.response.send_message(

            embed=embed,

            view=DeveloperPanelView(
                self.bot
            ),

            ephemeral=True
        )


async def setup(bot):

    await bot.add_cog(
        DeveloperPanelCog(bot)
    )
