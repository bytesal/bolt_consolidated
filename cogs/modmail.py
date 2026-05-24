import os
import discord
from discord import app_commands
from discord.ext import commands
import datetime

class TicketControls(discord.ui.View):
    def __init__(self, bot, ticket_user_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_user_id = ticket_user_id

    @discord.ui.button(label="Close Session", style=discord.ButtonStyle.red, custom_id="modmail_close_btn_default")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Core DB Connection Unavailable.", ephemeral=True)
        
        await db_cog.modmail_tickets.delete_one({"user_id": str(self.ticket_user_id)})
        await db_cog.modmail_stats.update_one(
            {"_id": str(interaction.user.id)},
            {"$set": {"name": interaction.user.name}, "$inc": {"tickets_closed": 1}},
            upsert=True
        )

        public_user = self.bot.get_user(int(self.ticket_user_id))
        if public_user:
            try:
                await public_user.send("🔒 Your secure support transmission link has been cleanly closed by staff.")
            except Exception:
                pass

        await interaction.channel.delete()

class ModmailCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
            
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return

        if isinstance(message.channel, discord.DMChannel):
            ticket = await db_cog.modmail_tickets.find_one({"user_id": str(message.author.id)})
            link = await db_cog.server_links.find_one()
            if not link:
                return
            
            staff_guild = self.bot.get_guild(link["staff_guild_id"])
            if not staff_guild:
                return

            if not ticket:
                overwrites = {
                    staff_guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    staff_guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                chan = await staff_guild.create_text_channel(name=f"ticket-{message.author.name}", overwrites=overwrites)
                
                await db_cog.modmail_tickets.insert_one({
                    "user_id": str(message.author.id),
                    "channel_id": str(chan.id),
                    "timestamp": datetime.datetime.utcnow()
                })
                
                embed = discord.Embed(title="Support Session Generated", description=f"Transmission from: {message.author.mention}", color=discord.Color.green())
                embed.add_field(name="Content Input", value=message.content)
                await chan.send(embed=embed, view=TicketControls(self.bot, message.author.id))
                await message.author.send("✅ Safe Link Established. Staff team has received your packet headers.")
            else:
                chan = staff_guild.get_channel(int(ticket["channel_id"]))
                if chan:
                    embed = discord.Embed(description=message.content, color=discord.Color.blue())
                    embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
                    await chan.send(embed=embed)

        elif isinstance(message.channel, discord.TextChannel):
            ticket = await db_cog.modmail_tickets.find_one({"channel_id": str(message.channel.id)})
            if ticket:
                user = self.bot.get_user(int(ticket["user_id"]))
                if user:
                    try:
                        embed = discord.Embed(description=message.content, color=discord.Color.orange())
                        embed.set_author(name=f"Staff Response ({message.author.name})", icon_url=message.author.display_avatar.url)
                        await user.send(embed=embed)
                    except discord.Forbidden:
                        await message.channel.send("❌ Error transmitting packet frames back to target destination down link.")

    @app_commands.command(name="staffstats", description="Retrieve operational performance tracking vectors and resolution metrics analytics.")
    async def staff_stats_report(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_messages and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Access Denied.", ephemeral=True)
            
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Core DB Connection Unavailable.", ephemeral=True)
            
        stats = await db_cog.modmail_stats.find().to_list(None)
        if not stats:
            return await interaction.response.send_message("📊 Data pools empty. Performance vectors tracking dry.")

        embed = discord.Embed(title="📊 Support Performance Matrices", color=discord.Color.gold())
        for st in stats:
            embed.add_field(name=st.get("name", "Unknown Operator"), value=f"Resolved Interfaces: `{st.get('tickets_closed', 0)}`", inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ModmailCog(bot))
