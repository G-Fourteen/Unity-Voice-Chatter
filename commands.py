import discord
from discord.ext import commands
from discord.ui import View, Button
from discord import ButtonStyle
import asyncio

class ModelSelectView(View):
    def __init__(self, models, user_id, guild_id, memory_manager, data_manager):
        super().__init__(timeout=60)
        self.models = models
        self.user_id = user_id
        self.guild_id = guild_id
        self.memory_manager = memory_manager
        self.data_manager = data_manager
        for model in self.models:
            button = Button(label=model["name"], style=ButtonStyle.grey)
            button.callback = self.create_callback(model["name"])
            self.add_item(button)

    def create_callback(self, model_name):
        async def callback(interaction):
            await self.select_model(interaction, model_name)
        return callback

    async def select_model(self, interaction, model_name):
        if str(interaction.user.id) != str(self.user_id):
            await interaction.response.send_message("Only the command issuer can select a model!", ephemeral=True)
            return

        await interaction.response.defer()

        if self.memory_manager.set_user_model(self.guild_id, self.user_id, model_name):
            self.memory_manager.user_model_histories.setdefault(self.guild_id, {}).setdefault(self.user_id, {})[model_name] = []
            await self.data_manager.save_data_async(self.memory_manager)

            embed = discord.Embed(
                title="Model Selected",
                description=f"You have selected **{model_name}** as your model.",
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            )

            for child in self.children:
                child.disabled = True
            await interaction.followup.send(embed=embed, view=self, ephemeral=True)
        else:
            embed = discord.Embed(
                title="Invalid Model",
                description=f"Model **{model_name}** not found. Try again.",
                color=0xff0000,
                timestamp=discord.utils.utcnow()
            )
            await interaction.followup.send(embed=embed, view=self, ephemeral=True)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

def setup_commands(bot, models):
    @bot.command(name="unityhelp")
    async def unityhelp(ctx):
        embed = discord.Embed(
            title="Unity Bot Help",
            description="Available commands and models:",
            color=0x00ff00,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(
            name="Commands",
            value="`!unityhelp` - Show this help\n`!setmodel` - Choose a model\n`!savememory <text>` - Save a memory\n`!wipe` - Clear chat history",
            inline=False
        )
        if models:
            model_list = "\n".join([f"**{m['name']}**: {m.get('description', 'No description')}" for m in models])
            embed.add_field(name="Available Models", value=model_list, inline=False)
        else:
            embed.add_field(name="Available Models", value="No models loaded.", inline=False)
        embed.set_footer(text="Unity | Pollinations.ai")
        await ctx.send(embed=embed)

    @bot.command(name="setmodel")
    async def setmodel(ctx):
        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id) if ctx.guild else "DM"
        if not models:
            embed = discord.Embed(
                title="No Models Available",
                description="No models loaded.",
                color=0xff0000,
                timestamp=discord.utils.utcnow()
            )
            await ctx.send(embed=embed)
            return

        await ctx.send(f"<@{user_id}>, check your DMs for model selection.")

        try:
            dm_channel = await ctx.author.create_dm()
            
            # Split models into chunks of 25 max per view
            chunk_size = 25
            model_chunks = [models[i:i + chunk_size] for i in range(0, len(models), chunk_size)]
            
            for idx, chunk in enumerate(model_chunks, start=1):
                embed = discord.Embed(
                    title=f"Select Your Model (Part {idx}/{len(model_chunks)})",
                    description="Choose a model below:",
                    color=0x3498db,
                    timestamp=discord.utils.utcnow()
                )
                view = ModelSelectView(chunk, user_id, guild_id, bot.memory_manager, bot.data_manager)
                message = await dm_channel.send(embed=embed, view=view)
                view.message = message
        except discord.Forbidden:
            await ctx.send(f"<@{user_id}>, please enable DMs from server members.")

    @bot.command(name="savememory")
    async def savememory(ctx, *, memory_text):
        channel_id = str(ctx.channel.id)
        user_id = str(ctx.author.id)
        bot.memory_manager.add_memory(channel_id, memory_text)
        await bot.data_manager.save_data_async(bot.memory_manager)

        embed = discord.Embed(
            title="Memory Saved",
            description=f"Saved: {memory_text}",
            color=0x00ff00,
            timestamp=discord.utils.utcnow()
        )
        await ctx.send(f"<@{user_id}>", embed=embed)