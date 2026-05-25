import discord
from discord import app_commands
from discord.ext import commands
import traceback
import io
import contextlib
import sys


class DeveloperCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id in self.bot.DEVELOPER_IDS

    @app_commands.command(name="load", description="Load a cog.")
    async def load(self, interaction: discord.Interaction, cog: str):
        await interaction.response.defer(ephemeral=True)
        extension = f"cogs.{cog}"
        if extension in self.bot.extensions:
            return await interaction.followup.send(f"⚠️ `{cog}` is already loaded.")
        try:
            await self.bot.load_extension(extension)
            await interaction.followup.send(f"✅ Loaded cog: `{cog}`")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed loading `{cog}`\n```py\n{e}\n```")

    @app_commands.command(name="reload", description="Reload a cog.")
    async def reload(self, interaction: discord.Interaction, cog: str):
        await interaction.response.defer(ephemeral=True)
        extension = f"cogs.{cog}"
        try:
            if extension in self.bot.extensions:
                await self.bot.reload_extension(extension)
                await interaction.followup.send(f"✅ Reloaded cog: `{cog}`")
            else:
                await self.bot.load_extension(extension)
                await interaction.followup.send(f"✅ Loaded cog: `{cog}`")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed processing `{cog}`\n```py\n{e}\n```")

    @app_commands.command(name="unload", description="Unload a cog.")
    async def unload(self, interaction: discord.Interaction, cog: str):
        await interaction.response.defer(ephemeral=True)
        extension = f"cogs.{cog}"
        if extension not in self.bot.extensions:
            return await interaction.followup.send(f"⚠️ `{cog}` is not loaded.")
        try:
            await self.bot.unload_extension(extension)
            await interaction.followup.send(f"✅ Unloaded cog: `{cog}`")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed unloading `{cog}`\n```py\n{e}\n```")

    @app_commands.command(name="shutdown", description="Shutdown the bot.")
    async def shutdown(self, interaction: discord.Interaction):
        await interaction.response.send_message("🛑 Shutting down...", ephemeral=True)
        await self.bot.close()

    @app_commands.command(name="restart", description="Restart the bot (Railway-safe).")
    async def restart(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔄 Restarting bot...", ephemeral=True)
        await self.bot.close()
        sys.exit(0)

    @app_commands.command(name="eval", description="Execute Python code.")
    async def eval(self, interaction: discord.Interaction, code: str):
        await interaction.response.defer(ephemeral=True)
        env = {
            "bot": self.bot,
            "discord": discord,
            "commands": commands,
            "interaction": interaction,
            "__import__": __import__,
        }
        stdout = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout):
                exec(f"async def func():\n" + "\n".join(f"    {line}" for line in code.split("\n")), env)
                result = await env["func"]()
            output = stdout.getvalue()
            if result is not None:
                output += str(result)
            if not output:
                output = "✅ Code executed successfully."
            await interaction.followup.send(f"```py\n{output[:1900]}\n```")
        except Exception:
            error = traceback.format_exc()
            await interaction.followup.send(f"```py\n{error[:1900]}\n```")


async def setup(bot):
    await bot.add_cog(DeveloperCog(bot))
