from redbot.core import Config, commands, bot
from discord.ext import tasks
import datetime, inspect

_COG_IDENTIFIER = 37619525 # I just randomly generated this.
_DEFAULT_RATE = 30

class ActiveRole(commands.Cog):
	"""Automatically assign and remove a role to members that have sent a message recently."""

	def __init__(self, bot: bot.Red):
		self.bot = bot

		self.config = Config.get_conf(self, identifier=_COG_IDENTIFIER, force_registration=True)
		self.default_global = {
			"rate": _DEFAULT_RATE,
			"spew": False
		}
		self.default_guild = {
			"enabled": False,
			"role": None,
			"days": 1,
			"ignored_channels": []
		}
		self.config.register_global(**self.default_global)
		self.config.register_guild(**self.default_guild)

	async def init_loop(self):
		rate = await self.config.rate()
		self._loop.change_interval(minutes=rate)
		await self._log("ActiveRole will update every " + str(rate) + " minutes starting now.")
		self._loop.start()

	def cog_unload(self):
		self._loop.cancel()

	async def _log(self, message: str):
		'''Print message with debug info to Redbot's stdout if spew is enabled.'''
		if(await self.config.spew()):
			print("[" + str(datetime.datetime.now().time()) + "] ActiveRole." + inspect.stack()[1].function + "(): " + message)

	async def _active_members(self, guild):
		active_members = []
		after = datetime.datetime.utcnow() - datetime.timedelta(days=int(await self.config.guild(guild).days())) # Using utcnow because it needs to be timezone-naive representing UTC time.
		members = [member for member in guild.members if not member.bot]
		channels = [channel for channel in guild.text_channels if channel.id not in await self.config.guild(guild).ignored_channels()]
		for channel in channels:
			#await self._log("Searching channel " + str(channel.id) + " (" + channel.name + ") for messages from " + str(len(members)) + " remaining members.")
			async for message in channel.history(limit=None, after=after, oldest_first=False):
				for member in members:
					if(member == message.author):
						active_members.append(member)
						members.remove(member)
						break
				if(len(members) == 0):
					break
		await self._log("Found " + str(len(active_members)) + " active members in " + guild.name + ".")
		return active_members # TODO: Cache?

	async def _update(self, guild):
		role = guild.get_role(await self.config.guild(guild).role())
		active_members = await self._active_members(guild)
		added = 0
		removed = 0
		for member in guild.members:
			if(member in active_members and role not in member.roles):
				await member.add_roles(role, reason="Added by ActiveRole cog for being active in the last " + str(await self.config.guild(guild).days()) + " days")
				added += 1
			elif(role in member.roles):
				await member.remove_roles(role, reason="Removed by ActiveRole cog for being inactive in the last " + str(await self.config.guild(guild).days()) + " days")
				removed += 1
		await self._log("Added role to " + str(added) + " and removed from " + str(removed) + " members on " + guild.name + ".")

	@tasks.loop(seconds=_DEFAULT_RATE)
	async def _loop(self):
		for guild in self.bot.guilds:
			if(await self.config.guild(guild).enabled()):
				await self._log("Automatically updating guild " + guild.name + ".")
				await self._update(guild)

	# ---COMMANDS---

	@commands.is_owner()
	@commands.command(name="activerolerate")
	async def rate(self, ctx: commands.Context, rate: int=None):
		"""Get or set how many minutes ActiveRole should update the active role on all guilds."""
		async with ctx.channel.typing():
			if(type(rate) == int):
				await self.config.rate.set(rate)
				self._loop.change_interval(minutes=rate)
				await ctx.send("ActiveRole now updates every " + str(rate) + " minutes.")
			else:
				await ctx.send("ActiveRole currently updates every " + str(await self.config.rate()) + " minutes.")

	@commands.is_owner()
	@commands.command(name="activerolespew")
	async def spew(self, ctx: commands.Context, enabled: bool=None):
		"""Get or set whether ActiveRole should print debug info in the Redbot stdout."""
		async with ctx.channel.typing():
			if(type(enabled) == bool):
				await self.config.spew.set(enabled)
				await ctx.send("ActiveRole spew is now " + ("enabled" if enabled else "disabled") + ".")
			else:
				await ctx.send("ActiveRole spew is currently " + ("enabled" if await self.config.spew() else "disabled") + ".")
			return

	@commands.guild_only()
	@commands.bot_has_permissions(manage_roles=True)
	@commands.admin_or_permissions(administrator=True)
	@commands.group(name="activerole")
	async def active_role(self, ctx: commands.Context):
		"""Automatically assign a role to members that have sent a message recently."""

	@active_role.command(name="enabled")
	async def enabled(self, ctx: commands.Context, enabled: bool=None):
		"""Get or set whether ActiveRole is enabled."""
		async with ctx.channel.typing():
			if(type(enabled) == bool):
				await self.config.guild(ctx.guild).enabled.set(enabled)
				await ctx.send("ActiveRole is now " + ("enabled" if enabled else "disabled") + ".")
			else:
				await ctx.send("ActiveRole is currently " + ("enabled" if await self.config.guild(ctx.guild).enabled() else "disabled") + ".")
			return

	@active_role.command(name="role")
	async def role(self, ctx: commands.Context, role: int=None):
		"""Get or set the active role's ID."""
		async with ctx.channel.typing():
			if(type(role) == int):
				await self.config.guild(ctx.guild).role.set(role)
				await ctx.send("ActiveRole's active role ID is now " + str(role) + " (" + ctx.guild.get_role(await self.config.guild(ctx.guild).role()).name + ").")
			else:
				if(await self.config.guild(ctx.guild).role() is None):
					await ctx.send("ActiveRole's active role ID is currently unset.")
				else:
					await ctx.send("ActiveRole's active role ID is currently " + str(await self.config.guild(ctx.guild).role()) + " (" + ctx.guild.get_role(await self.config.guild(ctx.guild).role()).name + ").")
			return

	@active_role.command(name="days")
	async def days(self, ctx: commands.Context, days: int=None):
		"""Get or set the max span of days since messaging allowed for a user to have the active role."""
		async with ctx.channel.typing():
			if(type(days) == int):
				await self.config.guild(ctx.guild).days.set(days)
				await ctx.send("ActiveRole's max span of days is now set to " + str(days) + ".")
			else:
				await ctx.send("ActiveRole's max span of days is currently set to " + str(await self.config.guild(ctx.guild).days()) + ".")
			return

	@active_role.command(name="list")
	async def list(self, ctx: commands.Context):
		"""Generate list of currently active members."""
		async with ctx.channel.typing():
			members = await self._active_members(ctx.guild)
			message = "There are currently " + str(len(members)) + " active members."
			for member in members:
				if(member.nick is None):
					message += "\n\t" + member.name
				else:
					message += "\n\t" + member.nick + " (" + member.name + ")"
			await ctx.send(message)
			return

	@active_role.command(name="update")
	async def update(self, ctx: commands.Context):
		"""Manually update active role of members in guild."""
		async with ctx.channel.typing():
			await self._update(ctx.guild)
			await ctx.send("Active roles updated.")
			return

	@active_role.group(name="ignored")
	async def ignored_channels(self, ctx: commands.Context):
		"""Channels to ignore when determining activity."""
	
	@ignored_channels.command(name="list")
	async def ignored_channels_list(self, ctx: commands.Context):
		"""List channels currently being ignored."""
		async with ctx.channel.typing():
			channels = await self.config.guild(ctx.guild).ignored_channels()
			message = "There are currently " + str(len(channels)) + " channels being ignored."
			for channel in channels:
				message += "\n\t" + str(channel) + " (" + ctx.guild.get_channel(channel).name + ")"
			await ctx.send(message)
			return
	
	@ignored_channels.command(name="add")
	async def ignored_channels_add(self, ctx: commands.Context, channel: int):
		"""Add a channel ID to the list to ignore."""
		async with ctx.channel.typing():
			if(ctx.guild.get_channel(channel) is None):
				await ctx.send(str(channel) + " isn't a valid channel ID.")
				return
			async with self.config.guild(ctx.guild).ignored_channels() as channels:
				if(channel in channels):
					await ctx.send(str(channel) + " (" + ctx.guild.get_channel(channel).name + ") is already being ignored.")
					return
				channels.append(channel)
			await ctx.send("Added " + str(channel) + " (" + ctx.guild.get_channel(channel).name + ") to list of ignored channels.")
			return

	@ignored_channels.command(name="remove")
	async def ignored_channels_remove(self, ctx: commands.Context, channel: int):
		"""Remove a channel ID from the list to ignore."""
		async with ctx.channel.typing():
			if(ctx.guild.get_channel(channel) is None):
				await ctx.send(str(channel) + " isn't a valid channel ID.")
				return
			async with self.config.guild(ctx.guild).ignored_channels() as channels:
				try:
					channels.remove(channel)
				except ValueError:
					await ctx.send(str(channel) + " (" + ctx.guild.get_channel(channel).name + ") isn't being ignored.")
					return
			await ctx.send("Removed " + str(channel) + " (" + ctx.guild.get_channel(channel).name + ") from list of ignored channels.")
			return