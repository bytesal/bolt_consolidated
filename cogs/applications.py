import os
import discord
from discord import app_commands
from discord.ext import commands
from bson import ObjectId
import datetime

class ReviewButtons(discord.ui.View):
    def __init__(self, bot, app_id, job_name):
        super().__init__(timeout=None)
        self.bot = bot
        self.app_id = app_id
        self.job_name = job_name

    @discord.ui.button(label="Accept Application", style=discord.ButtonStyle.green, custom_id="hr_accept_btn_persistent")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_roles and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Error: Invalid access metrics.", ephemeral=True)
        modal = DecisionModal(self.bot, self.app_id, self.job_name, "accepted")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Reject Application", style=discord.ButtonStyle.red, custom_id="hr_reject_btn_persistent")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_roles and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Error: Invalid access metrics.", ephemeral=True)
        modal = DecisionModal(self.bot, self.app_id, self.job_name, "rejected")
        await interaction.response.send_modal(modal)

class DecisionModal(discord.ui.Modal):
    def __init__(self, bot, app_id, job_name, decision):
        super().__init__(title="HR Assessment Validation")
        self.bot = bot
        self.app_id = app_id
        self.job_name = job_name
        self.decision = decision
        self.reason = discord.ui.TextInput(label="Decision Rationale", style=discord.TextStyle.paragraph, required=True)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Error: Core database engine link is broken.")
            
        try:
            app = await db_cog.applications.find_one({"_id": ObjectId(self.app_id)})
            if not app:
                return await interaction.followup.send("❌ Error: File trace broken in database context.")

            await db_cog.applications.update_one({"_id": ObjectId(self.app_id)}, {"$set": {"status": self.decision}})
            await db_cog.hr_logs.insert_one({
                "application_id": self.app_id,
                "reviewer_id": interaction.user.id,
                "reviewer_name": interaction.user.name,
                "decision": self.decision,
                "reason": self.reason.value,
                "timestamp": datetime.datetime.utcnow()
            })

            link = await db_cog.get_server_link(interaction.guild.id)
            if link:
                public_guild = self.bot.get_guild(link["public_guild_id"])
                if public_guild:
                    member = public_guild.get_member(int(app["user_id"]))
                    if member:
                        try:
                            embed = discord.Embed(
                                title="Application Review Verdict",
                                description=f"Your submittal regarding position **{self.job_name}** was **{self.decision.upper()}**.",
                                color=discord.Color.green() if self.decision == "accepted" else discord.Color.red()
                            )
                            embed.add_field(name="Assigned Reason", value=self.reason.value)
                            await member.send(embed=embed)
                        except Exception:
                            pass

            await interaction.followup.send(f"✅ Resolution archived as: {self.decision.upper()}")
        except Exception as e:
            await interaction.followup.send(f"❌ Structural exception during submittal updates: {e}")

class ApplicationModal(discord.ui.Modal):
    def __init__(self, bot, job_name, staff_guild_id):
        super().__init__(title=f"Application: {job_name}")
        self.bot = bot
        self.job_name = job_name
        self.staff_guild_id = staff_guild_id
        self.input_data = discord.ui.TextInput(label="Statement of Capability", style=discord.TextStyle.paragraph, required=True)
        self.add_item(self.input_data)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.followup.send("❌ Error: Core database engine link is broken.")
            
        res = await db_cog.applications.insert_one({
            "user_id": str(interaction.user.id),
            "username": interaction.user.name,
            "job_name": self.job_name,
            "content": self.input_data.value,
            "status": "pending",
            "timestamp": datetime.datetime.utcnow()
        })
        
        app_id = res.inserted_id
        staff_guild = self.bot.get_guild(self.staff_guild_id)
        if staff_guild:
            chan_doc = await db_cog.settings.find_one({"_id": f"hr_channel_{self.staff_guild_id}"})
            if chan_doc:
                channel = staff_guild.get_channel(int(chan_doc["value"]))
                if channel:
                    embed = discord.Embed(title=f"📥 New Submission: {self.job_name}", color=discord.Color.orange())
                    embed.add_field(name="Applicant User", value=f"{interaction.user.mention} ({interaction.user.id})")
                    embed.add_field(name="Submitted Statement", value=self.input_data.value, inline=False)
                    await channel.send(embed=embed, view=ReviewButtons(self.bot, str(app_id), self.job_name))

        await interaction.followup.send("✅ Document metrics transmitted to HR matrix cleanly.", ephemeral=True)

class ApplicationLaunchView(discord.ui.View):
    def __init__(self, bot, job_name, staff_guild_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.job_name = job_name
        self.staff_guild_id = staff_guild_id

    @discord.ui.button(label="Initialize Form", style=discord.ButtonStyle.blurple, custom_id="init_app_form_btn_persistent")
    async def open_form(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApplicationModal(self.bot, self.job_name, self.staff_guild_id))

class ApplicationsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sethrchannel", description="Configure the primary HR operations target log terminal channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def sethrchannel(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Access Refused.", ephemeral=True)
            
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Core DB Connection Unavailable.", ephemeral=True)
            
        await db_cog.settings.update_one({"_id": f"hr_channel_{interaction.guild.id}"}, {"$set": {"value": str(interaction.channel.id)}}, upsert=True)
        await interaction.response.send_message(f"✅ Processing Target set to {interaction.channel.mention} for structural verification.")

    @app_commands.command(name="deployappform", description="Stream the recruitment initiation terminal panel into the public target workspace.")
    @app_commands.describe(job_name="The explicit title descriptor designation of the open operational position.")
    @app_commands.checks.has_permissions(administrator=True)
    async def deployappform(self, interaction: discord.Interaction, job_name: str):
        if not interaction.user.guild_permissions.administrator and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Access Refused.", ephemeral=True)
            
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Core DB Connection Unavailable.", ephemeral=True)
            
        link = await db_cog.get_server_link(interaction.guild.id)
        if not link:
            return await interaction.response.send_message("❌ Connect architecture via linking tools execution configurations first.", ephemeral=True)

        public_guild = self.bot.get_guild(link["public_guild_id"])
        if public_guild:
            for channel in public_guild.text_channels:
                if channel.permissions_for(public_guild.me).send_messages:
                    embed = discord.Embed(
                        title=f"Recruitment Framework: {job_name}",
                        description="Press the initialization asset to interface with current operational vectors.",
                        color=discord.Color.blue()
                    )
                    await channel.send(embed=embed, view=ApplicationLaunchView(self.bot, job_name, interaction.guild.id))
                    return await interaction.response.send_message(f"✅ Portal opened inside public terminal channel: #{channel.name}")
                    
        await interaction.response.send_message("❌ Channel resolution error processing cross-server layout framework.")

    @app_commands.command(name="hrlogs", description="Retrieve audit logging metrics synced across application validation tasks.")
    @app_commands.describe(reviewer="Target staff user footprint parameter filter.")
    async def hr_logs(self, interaction: discord.Interaction, reviewer: discord.Member = None):
        if not interaction.user.guild_permissions.manage_messages and interaction.user.id not in self.bot.DEVELOPER_IDS:
            return await interaction.response.send_message("❌ Invalid Access Permissions.", ephemeral=True)
            
        db_cog = self.bot.get_cog("DatabaseCog")
        if not db_cog:
            return await interaction.response.send_message("❌ Core DB Connection Unavailable.", ephemeral=True)
            
        query = {"reviewer_id": reviewer.id} if reviewer else {}
        logs = await db_cog.hr_logs.find(query).sort("timestamp", -1).limit(10).to_list(None)
        
        if not logs:
            return await interaction.response.send_message("📋 Log stream dry. No events located.")
        
        embed = discord.Embed(title="System Audit Log Summary", color=discord.Color.purple())
        for log in logs:
            embed.add_field(
                name=f"ID Ref: {log.get('application_id')}",
                value=f"Decision: `{log['decision']}`\nReviewer: `{log['reviewer_name']}`\nReasoning: {log['reason']}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ApplicationsCog(bot))
