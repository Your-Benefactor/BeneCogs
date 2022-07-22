from .activerole import ActiveRole

async def setup(bot):
	cog = ActiveRole(bot)
	await cog.initLoop()
	bot.add_cog(cog)