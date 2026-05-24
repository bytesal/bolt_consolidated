import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio


TICKET_COOLDOWN = 300


class TicketCategoryView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def create_ticket(
        self,
        interaction: discord.Interaction,
        category_name: str
    ):
        db_cog = self.bot.get_cog("DatabaseCog")

        existing = await db_cog.modmail_tickets.find_one({
            "user_id": str(interaction.user.id),
            "status": "open"
        })

        if existing:
            return await interaction.response.send_message(
                "❌ You already have an open ticket.",
                ephemeral=True
            )

        config = await db_cog.settings.find_one({
            "_id": f"modmail_guild"
        })

        if not config:
            return await interaction.response.send_message(
                "❌ Modmail is not configured.",
                ephemeral=True
            )

        guild = self.bot.get_guild(
            int(config["guild_id"])
        )

        category = guild.get_channel(
            int(config["category_id"])
        )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                read_messages=False
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True
            )
        }

        channel = await guild.create_text_channel(
            name=f"{category_name}-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        await db_cog.modmail_tickets.insert_one({
            "user_id": str(interaction.user.id),
            "channel_id": str(channel.id),
            "category": category_name,
            "status": "open",
            "claimed_by": None,
            "opened_at": datetime.utcnow()
        })

        embed = discord.Embed(
            title="📩 New Ticket",
            color=discord.Color.green()
        )

        embed.add_field(
            name="User",
            value=f"{interaction.user.mention}",
            inline=False
        )

        embed.add_field(
            name="Category",
            value=category_name,
            inline=False
        )

        await channel.send(
            embed=embed,
            view=TicketControls(self.bot, interaction.user.id)
        )

        await interaction.response.send_message(
            "✅ Ticket created successfully.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Support",
        style=discord.ButtonStyle.blurple
    )
    async def support(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.create_ticket(interaction, "support")

    @discord.ui.button(
        label="Report",
        style=discord.ButtonStyle.red
    )
    async def report(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.create_ticket(interaction, "report")

    @discord.ui.button(
        label="Partnership",
        style=discord.ButtonStyle.green
    )
    async def partnership(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.create_ticket(interaction, "partnership")


class TicketControls(discord.ui.View):
    def __init__(self, bot, user_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id

    @discord.ui.button(
        label="Claim",
        style=discord.ButtonStyle.blurple
    )
    async def claim(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        db_cog = self.bot.get_cog("DatabaseCog")

        await db_cog.modmail_tickets.update_one(
            {"channel_id": str(interaction.channel.id)},
            {"$set": {"claimed_by": str(interaction.user.id)}}
        )

        await interaction.response.send_message(
            f"✅ Ticket claimed by {interaction.user.mention}"
        )

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.red
    )
    async def close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        db_cog = self.bot.get_cog("DatabaseCog")

        ticket = await db_cog.modmail_tickets.find_one({
            "channel_id": str(interaction.channel.id)
        })

        if not ticket:
            return

        user = self.bot.get_user(
            int(ticket["user_id"])
        )

        if user:
            try:
                await user.send(
                    "🔒 Your ticket has been closed."
                )
            except Exception:
                pass

        await db_cog.modmail_tickets.update_one(
            {"channel_id": str(interaction.channel.id)},
            {
                "$set": {
                    "status": "closed",
                    "closed_at": datetime.utcnow()
                }
            }
        )

        await interaction.response.send_message(
            "🔒 Closing ticket..."
        )

        await asyncio.sleep(3)

        await interaction.channel.delete()


class ModmailCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}

    # =========================================================
    # CONFIG
    # =========================================================

    @app_commands.command(
        name="setupmodmail",
        description="Setup modmail."
    )
    async def setup_modmail(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel
    ):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Administrator required.",
                ephemeral=True
            )

        db_cog = self.bot.get_cog("DatabaseCog")

        await db_cog.settings.update_one(
            {"_id": "modmail_guild"},
            {
                "$set": {
                    "guild_id": str(interaction.guild.id),
                    "category_id": str(category.id)
                }
            },
            upsert=True
        )

        await interaction.response.send_message(
            "✅ Modmail configured successfully."
        )

    # =========================================================
    # DM LISTENER
    # =========================================================

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        db_cog = self.bot.get_cog("DatabaseCog")

        if isinstance(message.channel, discord.DMChannel):

            now = datetime.utcnow().timestamp()

            if message.author.id in self.cooldowns:
                diff = now - self.cooldowns[message.author.id]

                if diff < TICKET_COOLDOWN:
                    return await message.author.send(
                        "⏳ Please wait before opening another ticket."
                    )

            ticket = await db_cog.modmail_tickets.find_one({
                "user_id": str(message.author.id),
                "status": "open"
            })

            if not ticket:
                self.cooldowns[message.author.id] = now

                embed = discord.Embed(
                    title="Support Center",
                    description="Choose a category below.",
                    color=discord.Color.blurple()
                )

                return await message.author.send(
                    embed=embed,
                    view=TicketCategoryView(self.bot)
                )

            guild = self.bot.get_guild(
                int(
                    (
                        await db_cog.settings.find_one({
                            "_id": "modmail_guild"
                        })
                    )["guild_id"]
                )
            )

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
                    value="\n".join(a.url for a in message.attachments),
                    inline=False
                )

            await channel.send(embed=embed)

        else:
            ticket = await db_cog.modmail_tickets.find_one({
                "channel_id": str(message.channel.id),
                "status": "open"
            })

            if not ticket:
                return

            if message.author.bot:
                return

            user = self.bot.get_user(
                int(ticket["user_id"])
            )

            if not user:
                return

            embed = discord.Embed(
                description=message.content,
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )

            embed.set_author(
                name=f"Staff • {message.author.name}",
                icon_url=message.author.display_avatar.url
            )

            if message.attachments:
                embed.add_field(
                    name="Attachments",
                    value="\n".join(a.url for a in message.attachments),
                    inline=False
                )

            try:
                await user.send(embed=embed)
            except Exception:
                await message.channel.send(
                    "❌ Could not DM user."
                )


async def setup(bot):
    await bot.add_cog(ModmailCog(bot))
