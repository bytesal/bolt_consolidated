import discord
from discord.ext import commands
from discord import app_commands


# =========================================================
# STAFF TEAM DROPDOWN
# =========================================================

class StaffTeamDropdown(discord.ui.Select):

    def __init__(
        self,
        bot,
        teams
    ):

        self.bot = bot
        self.teams = teams

        options = []

        for team in teams:

            options.append(

                discord.SelectOption(

                    label=team["team_name"],

                    emoji=team.get(
                        "emoji",
                        "👥"
                    ),

                    description=team.get(
                        "description",
                        "No description provided."
                    )[:100]
                )
            )

        super().__init__(

            placeholder="Select a staff department...",

            min_values=1,
            max_values=1,

            options=options,

            custom_id="staff_team_dropdown"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        selected_team = self.values[0]

        team_data = None

        for team in self.teams:

            if (
                team["team_name"]
                == selected_team
            ):

                team_data = team
                break

        if not team_data:

            return await interaction.response.send_message(
                "❌ Team not found.",
                ephemeral=True
            )

        guild = interaction.guild

        member_mentions = []

        for member_id in team_data.get(
            "members",
            []
        ):

            member = guild.get_member(
                int(member_id)
            )

            if member:

                member_mentions.append(
                    member.mention
                )

        if not member_mentions:

            member_mentions = [
                "No members assigned."
            ]

        responsibilities = team_data.get(
            "responsibilities",
            []
        )

        if not responsibilities:

            responsibilities = [
                "No responsibilities configured."
            ]

        embed = discord.Embed(

            title=(
                f"{team_data.get('emoji', '👥')} "
                f"{team_data['team_name']}"
            ),

            description=team_data.get(
                "description",
                "No description provided."
            ),

            color=discord.Color.blurple()
        )

        embed.add_field(

            name="👥 Team Members",

            value="\n".join(
                member_mentions
            ),

            inline=False
        )

        embed.add_field(

            name="📋 Responsibilities",

            value="\n".join(
                f"• {r}"
                for r in responsibilities
            ),

            inline=False
        )

        embed.add_field(

            name="🤝 How They Help",

            value=team_data.get(
                "support_text",
                "No support information provided."
            ),

            inline=False
        )

        embed.set_footer(
            text=f"{guild.name}"
        )

        if guild.icon:

            embed.set_thumbnail(
                url=guild.icon.url
            )

        await interaction.response.edit_message(
            embed=embed,
            view=self.view
        )


# =========================================================
# STAFF TEAM VIEW
# =========================================================

class StaffTeamView(discord.ui.View):

    def __init__(
        self,
        bot,
        teams
    ):

        super().__init__(
            timeout=None
        )

        self.add_item(
            StaffTeamDropdown(
                bot,
                teams
            )
        )


# =========================================================
# STAFF COG
# =========================================================

class StaffCog(commands.Cog):

    def __init__(
        self,
        bot
    ):

        self.bot = bot

    # =====================================================
    # CREATE TEAM
    # =====================================================

    @app_commands.command(
        name="createteam",
        description="Create a staff team."
    )

    @app_commands.default_permissions(
        administrator=True
    )

    async def create_team(
        self,
        interaction: discord.Interaction,
        name: str,
        emoji: str,
        description: str,
        support_text: str
    ):

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        existing = await db_cog.staff_teams.find_one({

            "team_name": name,
            "guild_id": str(interaction.guild.id)
        })

        if existing:

            return await interaction.response.send_message(

                "❌ A team with that name already exists.",

                ephemeral=True
            )

        await db_cog.staff_teams.insert_one({

            "guild_id": str(
                interaction.guild.id
            ),

            "team_name": name,

            "emoji": emoji,

            "description": description,

            "support_text": support_text,

            "responsibilities": [],

            "members": []
        })

        await interaction.response.send_message(

            f"✅ Staff team `{name}` created successfully."
        )

    # =====================================================
    # ADD MEMBER
    # =====================================================

    @app_commands.command(
        name="addmember",
        description="Add a member to a staff team."
    )

    @app_commands.default_permissions(
        administrator=True
    )

    async def add_member(
        self,
        interaction: discord.Interaction,
        team: str,
        member: discord.Member
    ):

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        data = await db_cog.staff_teams.find_one({

            "team_name": team,
            "guild_id": str(interaction.guild.id)
        })

        if not data:

            return await interaction.response.send_message(

                "❌ Team not found.",

                ephemeral=True
            )

        await db_cog.staff_teams.update_one(

            {
                "team_name": team,
                "guild_id": str(interaction.guild.id)
            },

            {
                "$addToSet": {
                    "members": member.id
                }
            }
        )

        await interaction.response.send_message(

            f"✅ {member.mention} added to `{team}`."
        )

    # =====================================================
    # REMOVE MEMBER
    # =====================================================

    @app_commands.command(
        name="removemember",
        description="Remove a member from a staff team."
    )

    @app_commands.default_permissions(
        administrator=True
    )

    async def remove_member(
        self,
        interaction: discord.Interaction,
        team: str,
        member: discord.Member
    ):

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        await db_cog.staff_teams.update_one(

            {
                "team_name": team,
                "guild_id": str(interaction.guild.id)
            },

            {
                "$pull": {
                    "members": member.id
                }
            }
        )

        await interaction.response.send_message(

            f"✅ {member.mention} removed from `{team}`."
        )

    # =====================================================
    # ADD RESPONSIBILITY
    # =====================================================

    @app_commands.command(
        name="addresponsibility",
        description="Add a responsibility to a team."
    )

    @app_commands.default_permissions(
        administrator=True
    )

    async def add_responsibility(
        self,
        interaction: discord.Interaction,
        team: str,
        responsibility: str
    ):

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        await db_cog.staff_teams.update_one(

            {
                "team_name": team,
                "guild_id": str(interaction.guild.id)
            },

            {
                "$addToSet": {
                    "responsibilities": responsibility
                }
            }
        )

        await interaction.response.send_message(

            f"✅ Responsibility added to `{team}`."
        )

    # =====================================================
    # POST STAFF PANEL
    # =====================================================

    @app_commands.command(
        name="poststaffpanel",
        description="Post the public staff panel."
    )

    @app_commands.default_permissions(
        administrator=True
    )

    async def post_staff_panel(
        self,
        interaction: discord.Interaction
    ):

        db_cog = self.bot.get_cog(
            "DatabaseCog"
        )

        teams = await db_cog.staff_teams.find({

            "guild_id": str(
                interaction.guild.id
            )

        }).to_list(None)

        if not teams:

            return await interaction.response.send_message(

                "❌ No staff teams configured.",

                ephemeral=True
            )

        embed = discord.Embed(

            title="👥 Staff Directory",

            description=(
                "Select a department from the "
                "dropdown menu below to view "
                "team members, responsibilities, "
                "and support information."
            ),

            color=discord.Color.blurple()
        )

        if interaction.guild.icon:

            embed.set_thumbnail(
                url=interaction.guild.icon.url
            )

        embed.set_footer(
            text=interaction.guild.name
        )

        await interaction.channel.send(

            embed=embed,

            view=StaffTeamView(
                self.bot,
                teams
            )
        )

        await interaction.response.send_message(

            "✅ Staff panel deployed successfully.",

            ephemeral=True
        )


# =========================================================
# SETUP
# =========================================================

async def setup(bot):

    await bot.add_cog(
        StaffCog(bot)
    )
