import os
import discord
from discord import app_commands
from discord.ext import commands

class CoreCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_dev(self, user_id: int) -> bool:
        return user_id in self.bot.DEVELOPER_IDS

    async def clean_permission_check(self, interaction: discord.Interaction, perm: str = None) -> bool:
        if self.is_dev(interaction.user.id):
            return True
        if perm and hasattr(interaction.user.guild_permissions, perm):
            return getattr(interaction.user.guild_permissions, perm)
        return interaction.user.guild_permissions.administrator

    @app_commands.command(name="linkserver", description="Interconnect staff server framework with a target public server.")
    @app_commands.describe(public_guild_id="The explicit Snowflake ID designation of the target public guild configuration.")
    async def link_server_command(self, interaction: discord.Interaction, public_guild_id: str):
        if not await self.clean_permission_check(interaction):
            return await interaction.response.send_message("❌ Access Denied: Administrator permission or Developer identity verification failed.", ephemeral=True)
        
        try:
            target_id = int(public_guild_id)
        except ValueError:
            return await interaction.response.send_message("❌ Error: Provided public server ID must be a valid numerical sequence.", ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Core DB Connection Unavailable.", ephemeral=True)

        await db_cog.link_servers(interaction.guild.id, target_id)
        
        embed = discord.Embed(
            title="Server Inter-Link Implemented",
            description=f"This channel cluster has been defined as the **Staff Server**.\nLinked Public Server Target: `{target_id}`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="setprefix", description="Alter dynamic routing parameter configurations for standard prefix validation.")
    @app_commands.describe(prefix="The new character symbol sequence string designation.")
    async def set_prefix_command(self, interaction: discord.Interaction, prefix: str):
        if not await self.clean_permission_check(interaction):
            return await interaction.response.send_message("❌ Access Denied: Missing administrative permissions.", ephemeral=True)
            
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Core DB Connection Unavailable.", ephemeral=True)

        await db_cog.set_guild_prefix(interaction.guild.id, prefix)
        await interaction.response.send_message(f"✅ Executed: Prefix updated to `{prefix}` for this guild.")

    @app_commands.command(name="botstatus", description="Force universal system presence override states across global processing matrices.")
    @app_commands.describe(
        status_type="The online visibility metrics type parameter (online, idle, dnd, invisible).",
        activity_text="The customized text visual payload string to display inside presence feeds."
    )
    async def bot_status_command(self, interaction: discord.Interaction, status_type: str, activity_text: str):
        if not self.is_dev(interaction.user.id):
            return await interaction.response.send_message("❌ Core Security Error: Command limited to Global System Developers.", ephemeral=True)
        
        status_map = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible
        }
        status = status_map.get(status_type.lower(), discord.Status.online)
        activity = discord.Game(name=activity_text)
        await self.bot.change_presence(status=status, activity=activity)
        await interaction.response.send_message("✅ System Presence modifications pushed to API successfully.")

    @app_commands.command(name="setbotname", description="Alter global core identity naming structures assigned onto the application client profile.")
    @app_commands.describe(new_name="The complete new username identity designation string.")
    async def set_bot_name_command(self, interaction: discord.Interaction, new_name: str):
        if not self.is_dev(interaction.user.id):
            return await interaction.response.send_message("❌ Core Security Error: Command limited to Global System Developers.", ephemeral=True)
        try:
            await self.bot.user.edit(username=new_name)
            await interaction.response.send_message(f"✅ System application identity renamed to: **{new_name}**")
        except Exception as e:
            await interaction.response.send_message(f"❌ API Identity Assignment Refused: {e}", ephemeral=True)

    @app_commands.command(name="help", description="Retrieve the structured operational assistance catalog for localized workspace contexts.")
    async def comprehensive_help(self, interaction: discord.Interaction):
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Core DB Connection Unavailable.", ephemeral=True)

        is_staff = await db_cog.get_server_link(interaction.guild.id)
        is_public = await db_cog.get_link_by_public(interaction.guild.id)

        embed = discord.Embed(
            title="⚡ Comprehensive System Operations Core",
            description="Dynamically adapting visual indexing to your local execution scope.",
            color=discord.Color.blue()
        )

        if is_staff or self.is_dev(interaction.user.id):
            embed.add_field(
                name="🛡️ Staff Server Executive Commands",
                value=(
                    "`/linkserver <Public ID>` - Interconnect server frames\n"
                    "`/setprefix <Symbol>` - Alter dynamic routing parameters\n"
                    "`/setwelcome <Channel ID> <Message>` - Stage public greetings\n"
                    "`/setleave <Channel ID> <Message>` - Stage departure alerts\n"
                    "`/sethrchannel` - Declare active application routing context\n"
                    "`/deployappform <Job>` - Deploy recruitment interface panels\n"
                    "`/hrlogs [Staff]` - Interrogate system log databases\n"
                    "`/addrank <Name> <Emoji> <Description>` - Generate duty interfaces\n"
                    "`/addduty <Rank> <Responsibility>` - Bind specific requirements\n"
                    "`/removedepartment <Staff ID>` - Purge individual from specialized allocations\n"
                    "`/shift` / `/quota` - Access workload matrices manually"
                ),
                inline=False
            )

        if is_public or not is_staff:
            embed.add_field(
                name="🌍 Main Public Server Commands",
                value=(
                    "`/rank` - Evaluate localized structural leveling values\n"
                    "`/apply` - Trigger standard application request process\n"
                    "`/warn` / `/adwarn` - Trigger tracking systems (For allocated mods inside tracking context)\n"
                    "`/sticky` - Fix visual elements directly to local terminal streams"
                ),
                inline=False
            )

        if self.is_dev(interaction.user.id):
            embed.add_field(
                name="🔧 Global Infrastructure Overrides (Dev Only)",
                value="`/botstatus <Type> <Text>` - Force presence states\n`/setbotname <Name>` - Change API application identity",
                inline=False
            )

        embed.set_footer(text="Bolt Multi-Server Platform Protocol v2.5 • Zero Shortcuts")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(CoreCog(bot))
