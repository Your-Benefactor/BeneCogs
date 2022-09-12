from .nocap import NoCap

async def setup(bot):
	cog = NoCap(bot)
	#await cog.init_loop()
	bot.add_cog(cog)