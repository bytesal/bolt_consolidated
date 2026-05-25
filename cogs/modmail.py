import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio
import os
from utils.logger import get_logger

logger = get_logger("modmail")
TICKET_COOLDOWN = 60

TRANSCRIPT_TEMPLATE = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Modmail Transcript - {ticket_id}</title></head>
<body style="font-family: sans-serif; background: #2f3136; color: #fff; padding: 20px;">
<h2>Modmail Transcript</h2>
<p><strong>User:</strong> {user_name} ({user_id})</p>
<p><strong>Category:</strong> {category}</p>
<p><strong>Opened:</strong> {opened_at}</p>
<p><strong>Closed:</strong> {closed_at}</p>
<hr>
{messages}
</body>
</html>"""


class TicketCategorySelect(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            discord.SelectOption(label="Support", description="General support ticket.", emoji="🛠️"),
            discord.SelectOption(label="Report", description="Report a user or issue.", emoji="🚨"),
            discord.SelectOption(label="Partnership", description="Business or partnership inquiry.", emoji="🤝")
        ]
        super().__init__(placeholder="Choose a ticket category...", min_values=1, max_values=1,
                         options=options, custom_id="ticket_category_select")

    async def callback(self, interaction: discord.Interaction):
        cog = self.bot.get_cog("ModmailCog")
        if not cog:
            return await interaction.response.send_message("❌ Modmail system unavailable.", ephemeral=True)
        await cog.create_ticket(interaction, self.values[0])


class TicketCategoryView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect(bot))


class OpenTicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.blurple, emoji="📩", custom_id="create_ticket_button")
    async def create_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📩 Support Center",
            description="Please choose a category below to open a support ticket.",
            color=discord.Color.gold()
        )
        embed.add_field(name="Categories", value="🛠️ Support\n🚨 Report\n🤝 Partnership", inline=False)
        embed.set_footer(text="Check your DMs after clicking.")
        try:
            await interaction.user.send(embed=embed, view=TicketCategoryView(interaction.client))
            await interaction.response.send_message("📨 Check your DMs.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I couldn't DM you. Please enable Direct Messages.", ephemeral=True)


class TicketControls(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, emoji="🛄", custom_id="claim_ticket_button")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database error.", ephemeral=True)
        ticket = await db_cog.modmail_tickets.find_one({"channel_id": str(interaction.channel.id), "status": "open"})
        if not ticket:
            return await interaction.followup.send("❌ Ticket not found.", ephemeral=True)
        result = await db_cog.modmail_tickets.update_one(
            {"_id": ticket["_id"], "claimed_by": None},
            {"$set": {"claimed_by": str(interaction.user.id), "claimed_at": datetime.utcnow()}}
        )
        if result.modified_count == 0:
            return await interaction.followup.send("❌ This ticket is already claimed by another staff member.", ephemeral=True)
        embed = discord.Embed(description=f"🛄 Ticket claimed by {interaction.user.mention}", color=discord.Color.green())
        await interaction.followup.send(embed=embed)
        logger.info(f"Ticket {ticket['_id']} claimed by {interaction.user.id}")

    @discord.ui.button(label="Unclaim", style=discord.ButtonStyle.grey, emoji="🔄", custom_id="unclaim_ticket_button")
    async def unclaim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database error.", ephemeral=True)
        ticket = await db_cog.modmail_tickets.find_one({"channel_id": str(interaction.channel.id), "status": "open"})
        if not ticket:
            return await interaction.followup.send("❌ Ticket not found.", ephemeral=True)
        await db_cog.modmail_tickets.update_one(
            {"_id": ticket["_id"]},
            {"$set": {"claimed_by": None, "claimed_at": None}}
        )
        embed = discord.Embed(description=f"🔄 Ticket unclaimed by {interaction.user.mention}", color=discord.Color.blue())
        await interaction.followup.send(embed=embed)
        logger.info(f"Ticket {ticket['_id']} unclaimed by {interaction.user.id}")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, emoji="🔒", custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        cog = self.bot.get_cog("ModmailCog")
        if not cog:
            return
        db_cog = cog.get_database_cog()
        if not db_cog:
            return
        ticket = await db_cog.modmail_tickets.find_one({"channel_id": str(interaction.channel.id), "status": "open"})
        if not ticket:
            return await interaction.followup.send("❌ Ticket not found.", ephemeral=True)

        closed_at = datetime.utcnow()
        await db_cog.modmail_tickets.update_one(
            {"_id": ticket["_id"]},
            {"$set": {"status": "closed", "closed_at": closed_at, "claimed_by": None}}
        )

        # Generate transcript
        messages = await db_cog.ticket_messages.find({"ticket_id": ticket["_id"]}).sort("timestamp", 1).to_list(None)
        transcript = await cog.generate_transcript(ticket, messages, closed_at)
        config = await db_cog.settings.find_one({"_id": f"modmail_config_{interaction.guild.id}"})
        if config and config.get("transcript_channel_id"):
            transcript_channel = self.bot.get_channel(int(config["transcript_channel_id"]))
            if transcript_channel:
                file = discord.File(transcript, filename=f"transcript_{ticket['_id']}.html")
                await transcript_channel.send(f"📜 Ticket #{ticket['_id']} closed by {interaction.user.mention}", file=file)
        try:
            os.remove(transcript)
        except:
            pass

        try:
            user = await self.bot.fetch_user(int(ticket["user_id"]))
            await user.send("🔒 Your support ticket has been closed. A transcript has been saved.")
        except Exception:
            pass

        await interaction.followup.send("🔒 Closing ticket...")
        await asyncio.sleep(3)
        await interaction.channel.delete()
        logger.info(f"Ticket {ticket['_id']} closed")


class ModmailCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}

    def get_database_cog(self):
        for name in ["DatabaseCog", "DatabaseHandler", "Database"]:
            cog = self.bot.get_cog(name)
            if cog:
                return cog
        return None

    async def generate_transcript(self, ticket, messages, closed_at) -> str:
        msgs_html = ""
        for msg in messages:
            timestamp = msg["timestamp"].strftime("%Y-%m-%d %H:%M:%S UTC")
            author = msg["author_name"]
            content = msg["content"].replace("\n", "<br>")
            msgs_html += f"""
            <div style="border-bottom: 1px solid #40444b; padding: 10px;">
                <strong>{author}</strong> <span style="color: #b9bbbe; font-size:0.8em;">{timestamp}</span><br>
                <span>{content}</span>
                {'' if not msg.get('attachments') else '<br><span style="font-size:0.8em;">📎 ' + ', '.join(msg['attachments']) + '</span>'}
            </div>
            """
        html = TRANSCRIPT_TEMPLATE.format(
            ticket_id=ticket["_id"],
            user_name=ticket.get("user_name", "Unknown"),
            user_id=ticket["user_id"],
            category=ticket.get("category", "Unknown"),
            opened_at=ticket["created_at"].strftime("%Y-%m-%d %H:%M:%S UTC"),
            closed_at=closed_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            messages=msgs_html
        )
        filename = f"transcript_{ticket['_id']}.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
        return filename

    @app_commands.command(name="setupmodmail", description="Setup the modmail category and transcript channel.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 30)
    async def setupmodmail(self, interaction: discord.Interaction, category: discord.CategoryChannel, transcript_channel: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.get_database_cog()
        if not db_cog:
            return await interaction.followup.send("❌ Database system unavailable.", ephemeral=True)
        await db_cog.settings.update_one(
            {"_id": f"modmail_config_{interaction.guild.id}"},
            {"$set": {
                "guild_id": str(interaction.guild.id),
                "category_id": str(category.id),
                "transcript_channel_id": str(transcript_channel.id) if transcript_channel else None
            }},
            upsert=True
        )
        await interaction.followup.send(
            f"✅ Modmail configured.\n📂 Category: {category.mention}\n📜 Transcripts: {transcript_channel.mention if transcript_channel else 'Not set'}"
        )
        logger.info(f"Modmail configured by {interaction.user.id} in {interaction.guild.id}")

    @app_commands.command(name="panel", description="Send the modmail panel.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 10)
    async def panel(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(
            title="📩 Support & Assistance Center",
            description="Need help from the staff team?\n\nClick the button below to create a ticket.",
            color=discord.Color.gold()
        )
        embed.add_field(name="Categories", value="🛠️ Support\n🚨 Reports\n🤝 Partnerships", inline=False)
        embed.add_field(name="Rules", value="• Do not spam tickets.\n• Be respectful.\n• Explain your issue clearly.", inline=False)
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text=f"{interaction.guild.name} Support System")
        await interaction.followup.send(embed=embed, view=OpenTicketButton())

    async def create_ticket(self, interaction: discord.Interaction, category_name: str):
        db_cog = self.get_database_cog()
        if not db_cog:
            return
        config = await db_cog.settings.find_one({"_id": f"modmail_config_{interaction.guild.id}"})
        if not config:
            return await interaction.response.send_message("❌ Modmail has not been configured. Run `/setupmodmail` first.", ephemeral=True)

        existing = await db_cog.modmail_tickets.find_one({"user_id": str(interaction.user.id), "status": "open", "guild_id": str(interaction.guild.id)})
        if existing:
            return await interaction.response.send_message("❌ You already have an open ticket in this server.", ephemeral=True)

        guild = interaction.guild
        category = guild.get_channel(int(config["category_id"]))
        if not category:
            return await interaction.response.send_message("❌ Modmail category not found. Re-run `/setupmodmail`.", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }
        # Add staff role permissions if configured
        staff_role_id = config.get("staff_role_id")
        if staff_role_id:
            staff_role = guild.get_role(int(staff_role_id))
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel_name = f"{category_name.lower()}-{interaction.user.name}"
        ticket_channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        ticket_doc = {
            "_id": str(ticket_channel.id),
            "guild_id": str(interaction.guild.id),
            "user_id": str(interaction.user.id),
            "user_name": interaction.user.name,
            "channel_id": str(ticket_channel.id),
            "category": category_name,
            "status": "open",
            "created_at": datetime.utcnow(),
            "closed_at": None,
            "claimed_by": None,
            "claimed_at": None
        }
        await db_cog.modmail_tickets.insert_one(ticket_doc)
        embed = discord.Embed(
            title="📩 New Modmail Ticket",
            description=f"User: {interaction.user.mention}\nCategory: **{category_name}**",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Instructions", value="Reply in this channel to respond to the user.\n⚠️ Your replies will be anonymized (shown as 'Management Team').\n🔒 Use the Claim button before handling to avoid conflicts.", inline=False)
        await ticket_channel.send(embed=embed, view=TicketControls(self.bot))
        await interaction.response.send_message("✅ Ticket created successfully. Please continue in DMs.", ephemeral=True)
        try:
            await interaction.user.send("✅ Your support ticket has been created. A staff member will assist you shortly.")
        except Exception:
            pass
        logger.info(f"Ticket {ticket_doc['_id']} created by user {interaction.user.id} in guild {interaction.guild.id}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        db_cog = self.get_database_cog()
        if not db_cog:
            return

        # User DM -> Staff channel
        if isinstance(message.channel, discord.DMChannel):
            # Find open ticket in any guild
            ticket = await db_cog.modmail_tickets.find_one({"user_id": str(message.author.id), "status": "open"})
            if ticket:
                guild = self.bot.get_guild(int(ticket["guild_id"]))
                if not guild:
                    return
                channel = guild.get_channel(int(ticket["channel_id"]))
                if not channel:
                    return
                embed = discord.Embed(description=message.content, color=discord.Color.blue(), timestamp=datetime.utcnow())
                embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
                attachments = []
                if message.attachments:
                    attachments = [a.url for a in message.attachments]
                    embed.add_field(name="Attachments", value="\n".join(attachments), inline=False)
                await channel.send(embed=embed)
                await db_cog.ticket_messages.insert_one({
                    "ticket_id": ticket["_id"],
                    "author_id": str(message.author.id),
                    "author_name": message.author.name,
                    "content": message.content,
                    "attachments": attachments,
                    "timestamp": datetime.utcnow(),
                    "direction": "user"
                })
                try:
                    await message.add_reaction("✅")
                except Exception:
                    pass
                return

            # Cooldown for new tickets
            now = datetime.utcnow().timestamp()
            if message.author.id in self.cooldowns and (now - self.cooldowns[message.author.id]) < TICKET_COOLDOWN:
                return await message.author.send("⏳ Please wait before opening another ticket.")
            self.cooldowns[message.author.id] = now
            embed = discord.Embed(title="📩 Support Center", description="This bot supports multiple servers. Which server do you need help with?\n\nRun `/panel` in the server where you need support to create a ticket.", color=discord.Color.gold())
            return await message.author.send(embed=embed)

        # Staff reply -> User (ANONYMIZED with claim lock)
        if message.guild:
            ticket = await db_cog.modmail_tickets.find_one({"channel_id": str(message.channel.id), "status": "open"})
            if not ticket:
                return
            # Check claim lock
            claimed_by = ticket.get("claimed_by")
            if claimed_by and claimed_by != str(message.author.id):
                try:
                    await message.delete()
                    await message.author.send(f"❌ This ticket is claimed by <@{claimed_by}>. Please unclaim it first or ask them to release it.")
                except Exception:
                    pass
                return
            # Auto‑claim on reply
            if not claimed_by:
                await db_cog.modmail_tickets.update_one(
                    {"_id": ticket["_id"]},
                    {"$set": {"claimed_by": str(message.author.id), "claimed_at": datetime.utcnow()}}
                )
                logger.info(f"Ticket {ticket['_id']} auto‑claimed by {message.author.id} on reply")
            try:
                user = await self.bot.fetch_user(int(ticket["user_id"]))
                embed = discord.Embed(description=message.content, color=discord.Color.gold(), timestamp=datetime.utcnow())
                embed.set_author(name="Management Team", icon_url=self.bot.user.display_avatar.url)
                attachments = []
                if message.attachments:
                    attachments = [a.url for a in message.attachments]
                    embed.add_field(name="Attachments", value="\n".join(attachments), inline=False)
                await user.send(embed=embed)
                await db_cog.ticket_messages.insert_one({
                    "ticket_id": ticket["_id"],
                    "author_id": str(message.author.id),
                    "author_name": message.author.display_name,
                    "content": message.content,
                    "attachments": attachments,
                    "timestamp": datetime.utcnow(),
                    "direction": "staff"
                })
                try:
                    await message.add_reaction("✅")
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Failed to relay staff reply to user {ticket['user_id']}: {e}")


async def setup(bot):
    await bot.add_cog(ModmailCog(bot))