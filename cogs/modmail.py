import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio

TICKET_COOLDOWN = 60


# =========================================================
# Ticket Category Dropdown
# =========================================================

class TicketCategorySelect(discord.ui.Select):

    def __init__(self, bot):

        self.bot = bot

        options = [
            discord.SelectOption(
                label="Support",
                description="General support ticket.",
                emoji="🛠️"
            ),
            discord.SelectOption(
                label="Report",
                description="Report a user or issue.",
                emoji="🚨"
            ),
            discord.SelectOption(
                label="Partnership",
                description="Business or partnership inquiry.",
                emoji="🤝"
            )
        ]

        super().__init__(
            placeholder="Choose a ticket category...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_category_select"
        )

    async def callback(self, interaction: discord.Interaction):

        category = self.values[0]

        cog = self.bot.get_cog("ModmailCog")

        if not cog:
            return await interaction.response.send_message(
                "❌ Modmail system unavailable.",
                ephemeral=True
            )

        await cog.create_ticket(
            interaction,
            category
        )


# =========================================================
# Ticket Category View
# =========================================================

class TicketCategoryView(discord.ui.View):

    def __init__(self, bot):
        super().__init__(timeout=None)

        self.bot = bot

        self.add_item(
            TicketCategorySelect(bot)
        )


# =========================================================
# Open Ticket Panel Button
# =========================================================

class OpenTicketButton(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.blurple,
        emoji="📩",
        custom_id="create_ticket_button"
    )
    async def create_ticket_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        embed = discord.Embed(
            title="📩 Support Center",
            description=(
                "Please choose a category below "
                "to open a support ticket."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Categories",
            value=(
                "🛠️ Support\n"
                "🚨 Report\n"
                "🤝 Partnership"
            ),
            inline=False
        )

        embed.set_footer(
            text="Check your DMs after clicking."
        )

        try:

            await interaction.user.send(
                embed=embed,
                view=TicketCategoryView(
                    interaction.client
                )
            )

            await interaction.response.send_message(
                "📨 Check your DMs.",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                (
                    "❌ I couldn't DM you.\n"
                    "Please enable Direct Messages."
                ),
                ephemeral=True
            )


# =========================================================
# Ticket Controls
# =========================================================

class TicketControls(discord.ui.View):

    def __init__(self, bot):
        super().__init__(timeout=None)

        self.bot = bot

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.green,
        emoji="🛄",
        custom_id="claim_ticket_button"
    )
    async def claim_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        embed = discord.Embed(
            description=(
                f"🛄 Ticket claimed by "
                f"{interaction.user.mention}"
            ),
            color=discord.Color.green()
        )

        await interaction.response.send_message(
            embed=embed
        )

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.red,
        emoji="🔒",
        custom_id="close_ticket_button"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        cog = self.bot.get_cog("ModmailCog")

        if not cog:
            return

        db_cog = cog.get_database_cog()

        if not db_cog:
            return

        ticket = await db_cog.modmail_tickets.find_one({
            "channel_id": str(interaction.channel.id),
            "status": "open"
        })

        if not ticket:

            return await interaction.response.send_message(
                "❌ Ticket not found.",
                ephemeral=True
            )

        await db_cog.modmail_tickets.update_one(
            {"_id": ticket["_id"]},
            {
                "$set": {
                    "status": "closed",
                    "closed_at": datetime.utcnow()
                }
            }
        )

        try:

            user = await self.bot.fetch_user(
                int(ticket["user_id"])
            )

            await user.send(
                "🔒 Your support ticket has been closed."
            )

        except Exception:
            pass

        await interaction.response.send_message(
            "🔒 Closing ticket..."
        )

        await asyncio.sleep(3)

        await interaction.channel.delete()


# =========================================================
# Modmail Cog
# =========================================================

class ModmailCog(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

        self.cooldowns = {}

    # =====================================================
    # Helpers
    # =====================================================

    def get_database_cog(self):

        for name in [
            "DatabaseCog",
            "DatabaseHandler",
            "Database"
        ]:

            cog = self.bot.get_cog(name)

            if cog:
                return cog

        return None

    # =====================================================
    # Setup Modmail
    # =====================================================

    @app_commands.command(
        name="setupmodmail",
        description="Setup the modmail category."
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def setupmodmail(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel
    ):

        db_cog = self.get_database_cog()

        if not db_cog:
            return await interaction.response.send_message(
                "❌ Database system unavailable.",
                ephemeral=True
            )

        await db_cog.settings.update_one(
            {"_id": "modmail_config"},
            {
                "$set": {
                    "guild_id": str(interaction.guild.id),
                    "category_id": str(category.id)
                }
            },
            upsert=True
        )

        await interaction.response.send_message(
            (
                f"✅ Modmail category set to "
                f"{category.mention}"
            )
        )

    # =====================================================
    # Send Panel
    # =====================================================

    @app_commands.command(
        name="panel",
        description="Send the modmail panel."
    )
    @app_commands.default_permissions(
        administrator=True
    )
    async def panel(
        self,
        interaction: discord.Interaction
    ):

        embed = discord.Embed(
            title="📩 Support & Assistance Center",
            description=(
                "Need help from the staff team?\n\n"
                "Click the button below to create a ticket."
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="Categories",
            value=(
                "🛠️ Support\n"
                "🚨 Reports\n"
                "🤝 Partnerships"
            ),
            inline=False
        )

        embed.add_field(
            name="Rules",
            value=(
                "• Do not spam tickets.\n"
                "• Be respectful.\n"
                "• Explain your issue clearly."
            ),
            inline=False
        )

        if interaction.guild.icon:

            embed.set_thumbnail(
                url=interaction.guild.icon.url
            )

        embed.set_footer(
            text=f"{interaction.guild.name} Support System"
        )

        await interaction.response.send_message(
            embed=embed,
            view=OpenTicketButton()
        )

    # =====================================================
    # Create Ticket
    # =====================================================

    async def create_ticket(
        self,
        interaction: discord.Interaction,
        category_name: str
    ):

        db_cog = self.get_database_cog()

        if not db_cog:
            return

        config = await db_cog.settings.find_one({
            "_id": "modmail_config"
        })

        if not config:

            return await interaction.response.send_message(
                (
                    "❌ Modmail has not been configured."
                ),
                ephemeral=True
            )

        existing_ticket = await db_cog.modmail_tickets.find_one({
            "user_id": str(interaction.user.id),
            "status": "open"
        })

        if existing_ticket:

            return await interaction.response.send_message(
                (
                    "❌ You already have an open ticket."
                ),
                ephemeral=True
            )

        guild = self.bot.get_guild(
            int(config["guild_id"])
        )

        if not guild:
            return

        category = guild.get_channel(
            int(config["category_id"])
        )

        if not category:
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),

            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),

            interaction.user: discord.PermissionOverwrite(
                view_channel=False
            )
        }

        channel_name = (
            f"{category_name.lower()}-"
            f"{interaction.user.name}"
        )

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        await db_cog.modmail_tickets.insert_one({

            "user_id": str(interaction.user.id),

            "channel_id": str(ticket_channel.id),

            "category": category_name,

            "status": "open",

            "created_at": datetime.utcnow()
        })

        embed = discord.Embed(
            title="📩 New Modmail Ticket",
            description=(
                f"User: {interaction.user.mention}\n"
                f"Category: **{category_name}**"
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(
            name="Instructions",
            value=(
                "Reply in this channel to "
                "respond to the user."
            ),
            inline=False
        )

        await ticket_channel.send(
            embed=embed,
            view=TicketControls(self.bot)
        )

        await interaction.response.send_message(
            (
                "✅ Ticket created successfully.\n"
                "Please continue in DMs."
            ),
            ephemeral=True
        )

        try:

            await interaction.user.send(
                (
                    "✅ Your support ticket "
                    "has been created."
                )
            )

        except Exception:
            pass

    # =====================================================
    # DM Relay System
    # =====================================================

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot:
            return

        db_cog = self.get_database_cog()

        if not db_cog:
            return

        # =================================================
        # USER DMS BOT
        # =================================================

        if isinstance(message.channel, discord.DMChannel):

            ticket = await db_cog.modmail_tickets.find_one({
                "user_id": str(message.author.id),
                "status": "open"
            })

            # =============================================
            # Existing Ticket
            # =============================================

            if ticket:

                guild = self.bot.get_guild(
                    int(
                        (
                            await db_cog.settings.find_one({
                                "_id": "modmail_config"
                            })
                        )["guild_id"]
                    )
                )

                if not guild:
                    return

                channel = guild.get_channel(
                    int(ticket["channel_id"])
                )

                if not channel:
                    return

                embed = discord.Embed(
                    description=message.content,
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )

                embed.set_author(
                    name=message.author.name,
                    icon_url=message.author.display_avatar.url
                )

                if message.attachments:

                    embed.add_field(
                        name="Attachments",
                        value="\n".join(
                            a.url
                            for a in message.attachments
                        ),
                        inline=False
                    )

                await channel.send(embed=embed)

                return

            # =============================================
            # Cooldown For New Tickets
            # =============================================

            now = datetime.utcnow().timestamp()

            if message.author.id in self.cooldowns:

                diff = (
                    now -
                    self.cooldowns[message.author.id]
                )

                if diff < TICKET_COOLDOWN:

                    return await message.author.send(
                        (
                            "⏳ Please wait before "
                            "opening another ticket."
                        )
                    )

            self.cooldowns[message.author.id] = now

            embed = discord.Embed(
                title="📩 Support Center",
                description=(
                    "Choose a category below."
                ),
                color=discord.Color.blurple()
            )

            return await message.author.send(
                embed=embed,
                view=TicketCategoryView(self.bot)
            )

        # =================================================
        # STAFF REPLY
        # =================================================

        if message.guild:

            ticket = await db_cog.modmail_tickets.find_one({
                "channel_id": str(message.channel.id),
                "status": "open"
            })

            if not ticket:
                return

            try:

                user = await self.bot.fetch_user(
                    int(ticket["user_id"])
                )

                embed = discord.Embed(
                    description=message.content,
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )

                embed.set_author(
                    name=f"{message.author}",
                    icon_url=message.author.display_avatar.url
                )

                if message.attachments:

                    embed.add_field(
                        name="Attachments",
                        value="\n".join(
                            a.url
                            for a in message.attachments
                        ),
                        inline=False
                    )

                await user.send(embed=embed)

            except Exception:
                pass


# =========================================================
# Setup
# =========================================================

async def setup(bot):

    await bot.add_cog(
        ModmailCog(bot)
    )
