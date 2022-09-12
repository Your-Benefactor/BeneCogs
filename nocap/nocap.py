from redbot.core import Config, commands, bot
from discord.ext import tasks
import datetime, inspect, discord


_COG_IDENTIFIER = 79789062 # I just randomly generated this.

class NoCap(commands.Cog):
	"""Respond to specific members that type in all capitals."""

	def __init__(self, bot: bot.Red):
		self.bot = bot

		self.config = Config.get_conf(self, identifier=_COG_IDENTIFIER, force_registration=True)
		#self.default_global = {}
		self.default_guild = {
			"enabled": False,
			"members": [],
			"message": ""
		}
		#self.config.register_global(**self.default_global)
		self.config.register_guild(**self.default_guild)

	@commands.Cog.listener("on_message")
	async def on_message(self, message: discord.Message):
		if message.author.bot:
			return
		guild: discord.Guild = getattr(message, "guild", None)
		if guild is None:
			return
		if await self.bot.cog_disabled_in_guild(self, guild):
			return
		if not await self.config.guild(guild).enabled():
			return
		if message.author.id not in await self.config.guild(guild).members():
			return
		if message.clean_content.isupper():
			await message.channel.send(await self.config.guild(guild).message())

	# ---COMMANDS---

	@commands.guild_only()
	@commands.admin_or_permissions(administrator=True)
	@commands.group(name="nocap")
	async def no_cap(self, ctx: commands.Context):
		"""Respond to specific members that type in all capitals."""

	@no_cap.command(name="enabled")
	async def enabled(self, ctx: commands.Context, enabled: bool=None):
		"""Get or set whether NoCap is enabled."""
		async with ctx.channel.typing():
			if(type(enabled) == bool):
				await self.config.guild(ctx.guild).enabled.set(enabled)
				await ctx.send("NoCap is now " + ("enabled" if enabled else "disabled") + ".")
			else:
				await ctx.send("NoCap is currently " + ("enabled" if await self.config.guild(ctx.guild).enabled() else "disabled") + ".")
			return

	@no_cap.command(name="message")
	async def message(self, ctx: commands.Context, message: str=None):
		"""Get or set the message to respond with."""
		async with ctx.channel.typing():
			if(type(message) == str):
				await self.config.guild(ctx.guild).message.set(message)
				await ctx.send("NoCap's message is now \"" + message + "\".")
			else:
				await ctx.send("NoCap's message is currently \"" + await self.config.guild(ctx.guild).message() + "\".")
			return

	@no_cap.group(name="members")
	async def members(self, ctx: commands.Context):
		"""Members to respond to."""
	
	@members.command(name="list")
	async def members_list(self, ctx: commands.Context):
		"""List members being responded to."""
		async with ctx.channel.typing():
			members = await self.config.guild(ctx.guild).members()
			message = "There are currently " + str(len(members)) + " member IDs being responded to."
			for member in members:
				message += "\n\t" + str(member) + " (" + ctx.guild.get_member(member).name + ")"
			await ctx.send(message)
			return
	
	@members.command(name="add")
	async def members_add(self, ctx: commands.Context, member: int):
		"""Add a member ID to the list to respond to."""
		async with ctx.channel.typing():
			if(ctx.guild.get_member(member) is None):
				await ctx.send(str(member) + " isn't a valid member ID.")
				return
			async with self.config.guild(ctx.guild).members() as members:
				if(member in members):
					await ctx.send(str(member) + " (" + ctx.guild.get_member(member).name + ") is already being responded to.")
					return
				members.append(member)
			await ctx.send("Added " + str(member) + " (" + ctx.guild.get_member(member).name + ") to list of member IDs being responded to.")
			return

	@members.command(name="remove")
	async def members_remove(self, ctx: commands.Context, member: int):
		"""Remove a member ID from the list to respond to."""
		async with ctx.channel.typing():
			if(ctx.guild.get_member(member) is None):
				await ctx.send(str(member) + " isn't a valid member ID.")
				return
			async with self.config.guild(ctx.guild).members() as members:
				try:
					members.remove(member)
				except ValueError:
					await ctx.send(str(member) + " (" + ctx.guild.get_member(member).name + ") isn't being responded to.")
					return
			await ctx.send("Removed " + str(member) + " (" + ctx.guild.get_member(member).name + ") from list of members being responded to.")
			return