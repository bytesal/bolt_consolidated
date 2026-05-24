import discord
from discord import app_commands
from discord.ext import commands
from bson import ObjectId
import datetime


# ---------------------------------------------------------------------------
# Review buttons — shown in the staff HR channel for each application
# ---------------------------------------------------------------------------

class ReviewButtons(discord.ui.View):
    def __init__(self, bot, app_id: str, job_name: str):
        super().__init__(timeout=None)
        self.bot      = bot
        self.app_id   = app_id
        self.job_name = job_name

    @discord.ui.button(
        label="Accept Application",
        style=discord.ButtonStyle.green,
        custom_id="hr_accept_btn_persistent",
    )
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (
            not interaction.user.guild_permissions.manage_roles
            and interaction.user.id not in self.bot.DEVELOPER_IDS
        ):
            return await interaction.response.send_message(
                "❌ You do not have permission to review applications.", ephemeral=True
            )
        await interaction.response.send_modal(
            DecisionModal(self.bot, self.app_id, self.job_name, "accepted")
        )

    @discord.ui.button(
        label="Reject Application",
        style=discord.ButtonStyle.red,
        custom_id="hr_reject_btn_persistent",
    )
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (
            not interaction.user.guild_permissions.manage_roles
            and interaction.user.id not in self.bot.DEVELOPER_IDS
        ):
            return await interaction.response.send_message(
                "❌ You do not have permission to review applications.", ephemeral=True
            )
        await interaction.response.send_modal(
            DecisionModal(self.bot, self.app_id, self.job_name, "rejected")
        )


# ---------------------------------------------------------------------------
# Modal shown after clicking Accept / Reject
# ---------------------------------------------------------------------------

class DecisionModal(discord.ui.Modal, title="HR Application Decision"):
    reason = discord.ui.TextInput(
        label="Decision Reason",
        style=discord.TextStyle.paragraph,
        required=True,
        placeholder="Provide a clear reason for this decision...",
    )

    def __init__(self, bot, app_id: str, job_name: str, decision: str):
        super().__init__()
        self.bot      = bot
        self.app_id   = app_id
        self.job_name = job_name
        self.decision = decision

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database connection unavailable.")

        try:
            app = await db_cog.applications.find_one({"_id": ObjectId(self.app_id)})
            if not app:
                return await interaction.followup.send("❌ Application record not found in database.")

            # Update application status
            await db_cog.applications.update_one(
                {"_id": ObjectId(self.app_id)},
                {"$set": {"status": self.decision}},
            )

            # Log the HR action
            await db_cog.hr_logs.insert_one(
                {
                    "application_id": self.app_id,
                    "reviewer_id":    interaction.user.id,
                    "reviewer_name":  interaction.user.name,
                    "decision":       self.decision,
                    "reason":         self.reason.value,
                    "timestamp":      datetime.datetime.utcnow(),
                }
            )

            # Notify the applicant via DM
            link = await db_cog.get_server_link(interaction.guild.id)
            if link:
                public_guild = self.bot.get_guild(link["public_guild_id"])
                if public_guild:
                    member = public_guild.get_member(int(app["user_id"]))
                    if member:
                        try:
                            embed = discord.Embed(
                                title="Application Decision",
                                description=(
                                    f"Your application for **{self.job_name}** has been "
                                    f"**{self.decision.upper()}**."
                                ),
                                color=(
                                    discord.Color.green()
                                    if self.decision == "accepted"
                                    else discord.Color.red()
                                ),
                            )
                            embed.add_field(name="Reason", value=self.reason.value)
                            await member.send(embed=embed)
                        except Exception:
                            pass  # DMs may be disabled — not a critical failure

            await interaction.followup.send(
                f"✅ Application has been marked as: **{self.decision.upper()}**"
            )

        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred while processing the decision: {e}")


# ---------------------------------------------------------------------------
# Modal shown to the applicant when they click "Apply"
# ---------------------------------------------------------------------------

class ApplicationModal(discord.ui.Modal, title="Staff Application Form"):
    statement = discord.ui.TextInput(
        label="Why do you want this position?",
        style=discord.TextStyle.paragraph,
        required=True,
        placeholder="Tell us about your experience and why you are a good fit...",
    )

    def __init__(self, bot, job_name: str, staff_guild_id: int):
        super().__init__()
        self.bot            = bot
        self.job_name       = job_name
        self.staff_guild_id = staff_guild_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Database connection unavailable.")

        # Save application to database
        res = await db_cog.applications.insert_one(
            {
                "user_id":   str(interaction.user.id),
                "username":  interaction.user.name,
                "job_name":  self.job_name,
                "content":   self.statement.value,
                "status":    "pending",
                "timestamp": datetime.datetime.utcnow(),
            }
        )

        app_id = res.inserted_id

        # Forward application to the staff HR channel
        staff_guild = self.bot.get_guild(self.staff_guild_id)
        if staff_guild:
            chan_doc = await db_cog.settings.find_one(
                {"_id": f"hr_channel_{self.staff_guild_id}"}
            )
            if chan_doc:
                channel = staff_guild.get_channel(int(chan_doc["value"]))
                if channel:
                    embed = discord.Embed(
                        title=f"📥 New Application: {self.job_name}",
                        color=discord.Color.orange(),
                    )
                    embed.add_field(
                        name="Applicant",
                        value=f"{interaction.user.mention} (`{interaction.user.id}`)",
                    )
                    embed.add_field(
                        name="Statement",
                        value=self.statement.value,
                        inline=False,
                    )
                    await channel.send(
                        embed=embed,
                        view=ReviewButtons(self.bot, str(app_id), self.job_name),
                    )

        await interaction.followup.send(
            "✅ Your application has been submitted successfully.", ephemeral=True
        )


# ---------------------------------------------------------------------------
# Button that opens the ApplicationModal — posted in the public server
# ---------------------------------------------------------------------------

class ApplicationLaunchView(discord.ui.View):
    def __init__(self, bot, job_name: str, staff_guild_id: int):
        super().__init__(timeout=None)
        self.bot            = bot
        self.job_name       = job_name
        self.staff_guild_id = staff_guild_id

    @discord.ui.button(
        label="Apply Now",
        style=discord.ButtonStyle.blurple,
        custom_id="init_app_form_btn_persistent",
    )
    async def open_form(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            ApplicationModal(self.bot, self.job_name, self.staff_guild_id)
        )


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class ApplicationsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # /sethrchannel — designate the current channel as the HR log channel
    # ------------------------------------------------------------------

    @app_commands.command(
        name="sethrchannel",
        description="Set the current channel as the HR applications log channel.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def sethrchannel(self, interaction: discord.Interaction):
        if (
            not interaction.user.guild_permissions.administrator
            and interaction.user.id not in self.bot.DEVELOPER_IDS
        ):
            return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)

        await db_cog.settings.update_one(
            {"_id": f"hr_channel_{interaction.guild.id}"},
            {"$set": {"value": str(interaction.channel.id)}},
            upsert=True,
        )
        await interaction.response.send_message(
            f"✅ HR log channel set to {interaction.channel.mention}."
        )

    # ------------------------------------------------------------------
    # /deployappform — post the application panel in the linked public server
    # ------------------------------------------------------------------

    @app_commands.command(
        name="deployappform",
        description="Deploy an application form panel to the linked public server.",
    )
    @app_commands.describe(job_name="The name of the position being advertised.")
    @app_commands.checks.has_permissions(administrator=True)
    async def deployappform(self, interaction: discord.Interaction, job_name: str):
        if (
            not interaction.user.guild_permissions.administrator
            and interaction.user.id not in self.bot.DEVELOPER_IDS
        ):
            return await interaction.response.send_message("❌ Administrator permission required.", ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)

        link = await db_cog.get_server_link(interaction.guild.id)
        if not link:
            return await interaction.response.send_message(
                "❌ This server is not linked to a public server. Use `/linkserver` first.",
                ephemeral=True,
            )

        public_guild = self.bot.get_guild(link["public_guild_id"])
        if not public_guild:
            return await interaction.response.send_message(
                "❌ Could not find the linked public server. Make sure the bot is in that server.",
                ephemeral=True,
            )

        # Find the first text channel the bot can send messages in
        for channel in public_guild.text_channels:
            if channel.permissions_for(public_guild.me).send_messages:
                embed = discord.Embed(
                    title=f"Now Hiring: {job_name}",
                    description="Click the button below to submit your application.",
                    color=discord.Color.blue(),
                )
                await channel.send(
                    embed=embed,
                    view=ApplicationLaunchView(self.bot, job_name, interaction.guild.id),
                )
                return await interaction.response.send_message(
                    f"✅ Application form deployed to #{channel.name} in the public server."
                )

        await interaction.response.send_message(
            "❌ No accessible text channels found in the public server.", ephemeral=True
        )

    # ------------------------------------------------------------------
    # /hrlogs — view recent HR decisions
    # ------------------------------------------------------------------

    @app_commands.command(
        name="hrlogs",
        description="View the latest HR application decisions.",
    )
    @app_commands.describe(reviewer="Filter logs by a specific staff member.")
    async def hr_logs(self, interaction: discord.Interaction, reviewer: discord.Member = None):
        if (
            not interaction.user.guild_permissions.manage_messages
            and interaction.user.id not in self.bot.DEVELOPER_IDS
        ):
            return await interaction.response.send_message("❌ Insufficient permissions.", ephemeral=True)

        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Database connection unavailable.", ephemeral=True)

        query = {"reviewer_id": reviewer.id} if reviewer else {}
        logs = await db_cog.hr_logs.find(query).sort("timestamp", -1).limit(10).to_list(None)

        if not logs:
            return await interaction.response.send_message("📋 No HR log entries found.")

        embed = discord.Embed(title="HR Action Log", color=discord.Color.purple())
        for log in logs:
            embed.add_field(
                name=f"App ID: {log.get('application_id')}",
                value=(
                    f"Decision: `{log['decision']}`\n"
                    f"Reviewer: `{log['reviewer_name']}`\n"
                    f"Reason: {log['reason']}"
                ),
                inline=False,
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(ApplicationsCog(bot))
