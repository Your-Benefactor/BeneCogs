from redbot.core import Config, commands
from discord.ext import tasks
import datetime

_COG_IDENTIFIER = 37619525 # I just randomly generated this.
_CHANNEL_HISTORY_LIMIT = 1000 # :(
_DEFAULT_RATE = 30

class ActiveRole(commands.Cog):
	"""Automatically assign and remove a role to members that have sent a message recently."""

	def __init__(self, bot):
		self.bot = bot

		self.config = Config.get_conf(self, identifier=_COG_IDENTIFIER, force_registration=True)
		self.default_global = {
			"rate": _DEFAULT_RATE
		}
		self.default_guild = {
			"enabled": False,
			"role": None,
			"days": 1
		}
		self.config.register_global(**self.default_global)
		self.config.register_guild(**self.default_guild)

	async def initLoop(self):
		await self.bot.wait_until_red_ready()
		self._loop.change_interval(minutes=await self.config.rate())
		self._loop.start()

	def cog_unload(self):
		self._loop.cancel()

	async def _active_members(self, guild):
		after = datetime.datetime.utcnow() - datetime.timedelta(days=int(await self.config.guild(guild).days())) # Using utcnow because it needs to be timezone-naive representing UTC time.
		members = guild.members
		active_members = []
		for channel in guild.text_channels: # TODO: Multithread.
			async for message in channel.history(limit=_CHANNEL_HISTORY_LIMIT, after=after):
				for member in members:
					if(member == message.author):
						active_members.append(member)
						members.remove(member)
						break
				if(len(members) == 0):
					break
		return active_members # TODO: Cache?

	async def _update(self, guild):
		role = guild.get_role(await self.config.guild(guild).role())
		active_members = await self._active_members(guild)
		for member in guild.members:
			if(member in active_members):
				await member.add_roles(role, reason="Added by ActiveRole cog for being active in the last " + str(await self.config.guild(guild).days()) + " days")
			elif(role in member.roles):
				await member.remove_roles(role, reason="Removed by ActiveRole cog for being inactive in the last " + str(await self.config.guild(guild).days()) + " days")

	@tasks.loop(seconds=_DEFAULT_RATE)
	async def _loop(self):
		for guild_id in await self.config.all_guilds():
			guild = self.bot.get_guild(guild_id)
			if(await self.config.guild(guild).enabled()):
				await self._update(guild)

	# ---COMMANDS---

	@commands.is_owner()
	@commands.command(name="activerole_rate")
	async def rate(self, ctx: commands.Context, rate: int=None):
		"""Get or set how many minutes ActiveRole should update the active role on all guilds."""
		if(type(rate) == int):
			await self.config.rate.set(rate)
			self._loop.change_interval(minutes=rate)
			await ctx.send("ActiveRole now updates every " + str(rate) + " minutes.")
		else:
			await ctx.send("ActiveRole currently updates every " + str(await self.config.rate()) + " minutes.")

	@commands.guild_only()
	@commands.bot_has_permissions(manage_roles=True)
	@commands.admin_or_permissions(administrator=True)
	@commands.group(name="activerole")
	async def active_role(self, ctx: commands.Context):
		"""Automatically assign a role to members that have sent a message recently."""

	@active_role.command(name="enabled")
	async def enabled(self, ctx: commands.Context, enabled: bool=None):
		"""Get or set whether ActiveRole is enabled."""
		if(type(enabled) == bool):
			await self.config.guild(ctx.guild).enabled.set(enabled)
			await ctx.send("ActiveRole is now " + ("enabled" if enabled else "disabled") + ".")
		else:
			await ctx.send("ActiveRole is currently " + ("enabled" if await self.config.guild(ctx.guild).enabled() else "disabled") + ".")

	@active_role.command(name="role")
	async def role(self, ctx: commands.Context, role: int=None):
		"""Get or set the active role's ID."""
		if(type(role) == int):
			await self.config.guild(ctx.guild).role.set(role)
			await ctx.send("ActiveRole's active role ID is now " + str(role) + ".")
		else:
			await ctx.send("ActiveRole's active role ID is currently " + str(await self.config.guild(ctx.guild).role()) + " (" + ctx.guild.get_role(await self.config.guild(ctx.guild).role()).name + ").")

	@active_role.command(name="days")
	async def days(self, ctx: commands.Context, days: int=None):
		"""Get or set the max span of days since messaging allowed for a user to have the active role."""
		if(type(days) == int):
			await self.config.guild(ctx.guild).days.set(days)
			await ctx.send("ActiveRole's max span of days is now set to " + str(days) + ".")
		else:
			await ctx.send("ActiveRole's max span of days is currently set to " + str(await self.config.guild(ctx.guild).days()) + ".")

	@active_role.command(name="list")
	async def list(self, ctx: commands.Context):
		"""Generate list of currently active members."""
		members = await self._active_members(ctx.guild)
		message = "There are currently " + str(len(members)) + " active members."
		for member in members:
			message += "\n\t" + member.name
		await ctx.send(message)

	@active_role.command(name="update")
	async def update(self, ctx: commands.Context):
		"""Manually update active role of members in guild."""
		await self._update(ctx.guild)
		await ctx.send("Active roles updated.")
