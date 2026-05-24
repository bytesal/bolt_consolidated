import discord
from discord import app_commands
from discord.ext import commands
import datetime


# ---------------------------------------------------------------------------
# Ticket close button — shown in the staff ticket channel
# ---------------------------------------------------------------------------

class TicketControls(discord.ui.View):
    def __init__(self, bot, ticket_user_id: int):
        super().__init__(timeout=None)
        self.bot            = bot
        self.ticket_user_id = ticket_user_id

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.red,
        custom_id="modmail_close_btn_default",
    )
    async def close_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send(
                "❌ Database connection unavailable.", ephemeral=True
            )

        # Remove ticket record
        await db_cog.modmail_tickets.delete_one({"user_id": str(self.ticket_user_id)})

        # Update closer's stats
        await db_cog.modmail_stats.update_one(
            {"_id": str(interaction.user.id)},
            {
                "$set": {"name": interaction.user.name},
                "$inc": {"tickets_closed": 1},
            },
            upsert=True,
        )

        # Notify the user that their ticket was closed
        public_user = self.bot.get_user(int(self.ticket_user_id))
        if public_user:
            try:
                await public_user.send(
                    "🔒 Your support ticket has been closed by a staff member."
                )
            except Exception:
                pass

        # Delete the ticket channel
        await interaction.channel.delete()


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class ModmailCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # Message listener — handles DM → staff forwarding and replies
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return

        # --- DM received from a user ---
        if isinstance(message.channel, discord.DMChannel):
            link = await db_cog.server_links.find_one()
            if not link:
                return

            staff_guild = self.bot.get_guild(link["staff_guild_id"])
            if not staff_guild:
                return

            ticket = await db_cog.modmail_tickets.find_one(
                {"user_id": str(message.author.id)}
            )

            if not ticket:
                # Create a new ticket channel in the staff server
                overwrites = {
                    staff_guild.default_role: discord.PermissionOverwrite(
                        read_messages=False
                    ),
                    staff_guild.me: discord.PermissionOverwrite(
                        read_messages=True, send_messages=True
                    ),
                }
                chan = await staff_guild.create_text_channel(
                    name=f"ticket-{message.author.name}",
                    overwrites=overwrites,
                )

                await db_cog.modmail_tickets.insert_one(
                    {
                        "user_id":    str(message.author.id),
                        "channel_id": str(chan.id),
                        "timestamp":  datetime.datetime.utcnow(),
                    }
                )

                embed = discord.Embed(
                    title="New Support Ticket",
                    description=f"Opened by: {message.author.mention} (`{message.author.id}`)",
                    color=discord.Color.green(),
                )
                embed.add_field(name="First Message", value=message.content, inline=False)
                await chan.send(
                    embed=embed,
                    view=TicketControls(self.bot, message.author.id),
                )
                await message.author.send(
                    "✅ Your ticket has been created. A staff member will respond shortly."
                )

            else:
                # Forward subsequent DM messages to the existing ticket channel
                chan = staff_guild.get_channel(int(ticket["channel_id"]))
                if chan:
                    embed = discord.Embed(
                        description=message.content,
                        color=discord.Color.blue(),
                    )
                    embed.set_author(
                        name=message.author.name,
                        icon_url=message.author.display_avatar.url,
                    )
                    await chan.send(embed=embed)

        # --- Staff reply in a ticket channel ---
        elif isinstance(message.channel, discord.TextChannel):
            ticket = await db_cog.modmail_tickets.find_one(
                {"channel_id": str(message.channel.id)}
            )
            if ticket:
                user = self.bot.get_user(int(ticket["user_id"]))
                if user:
                    try:
                        embed = discord.Embed(
                            description=message.content,
                            color=discord.Color.orange(),
                        )
                        embed.set_author(
                            name=f"Staff — {message.author.name}",
                            icon_url=message.author.display_avatar.url,
                        )
                        await user.send(embed=embed)
                    except discord.Forbidden:
                        await message.channel.send(
                            "❌ Could not deliver message — user has DMs disabled."
                        )

    # ------------------------------------------------------------------
    # /staffstats
    # ------------------------------------------------------------------

    @app_commands.command(
        name="staffstats",
        description="View ticket resolution statistics for all staff members.",
    )
    async def staff_stats_report(self, interaction: discord.Interaction):
        if (
            not interaction.user.guild_permissions.manage_messages
            and interaction.user.id not in self.bot.DEVELOPER_IDS
        ):
            return await interaction.response.send_message(
                "❌ Insufficient permissions.", ephemeral=True
            )

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message(
                "❌ Database connection unavailable.", ephemeral=True
            )

        stats = await db_cog.modmail_stats.find().to_list(None)
        if not stats:
            return await interaction.response.send_message(
                "📊 No ticket statistics found yet."
            )

        embed = discord.Embed(
            title="📊 Staff Ticket Statistics",
            color=discord.Color.gold(),
        )
        for st in stats:
            embed.add_field(
                name=st.get("name", "Unknown"),
                value=f"Tickets Closed: `{st.get('tickets_closed', 0)}`",
                inline=False,
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(ModmailCog(bot))
