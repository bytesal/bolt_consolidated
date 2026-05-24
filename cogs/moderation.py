# =========================================================
# PURGE
# =========================================================

@app_commands.command(
    name="purge",
    description="Delete a specific amount of messages."
)

@staff_or_developer(
    manage_messages=True
)

async def purge(
    self,
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(
        ephemeral=True
    )

    deleted = await interaction.channel.purge(
        limit=amount
    )

    await interaction.followup.send(
        f"✅ Deleted {len(deleted)} messages.",
        ephemeral=True
    )

# =========================================================
# PURGE USER
# =========================================================

@app_commands.command(
    name="purgeuser",
    description="Delete messages from a specific user."
)

@staff_or_developer(
    manage_messages=True
)

async def purge_user(
    self,
    interaction: discord.Interaction,
    user_id: str,
    amount: app_commands.Range[int, 1, 100]
):

    await interaction.response.defer(
        ephemeral=True
    )

    def check(message: discord.Message):

        return str(message.author.id) == user_id

    deleted = await interaction.channel.purge(
        limit=500,
        check=check
    )

    deleted = deleted[:amount]

    await interaction.followup.send(
        f"✅ Deleted {len(deleted)} messages from user `{user_id}`.",
        ephemeral=True
    )
