from .activerole import ActiveRole

async def setup(bot):
	cog = ActiveRole(bot)
	#await bot.wait_until_ready()
	await cog.init_loop()
	await bot.add_cog(cog)
