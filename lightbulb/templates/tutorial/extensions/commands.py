import hikari
import lightbulb
import miru
import datetime


plugin =lightbulb.Plugin("commands")            #Makes an instance of the plugin




def load(bot:lightbulb.app.BotApp):             #This is the function called when loading a plugin
    bot.add_plugin(plugin)




@plugin.command                                 #Assigning the command to the plugin. This must be either a plugin or BotApp instance followed by .command
@lightbulb.option("text",                       #The name of the option, MUST be lowercase
                   "The text to repeat",        #The description of the option, can be upper case
                   type=str)                    #The type of the imput of the option (whether it is a number, string or user (hikari.User))
@lightbulb.command("echo",                      #The name of the command. MUST be lowercase and after all options
                   "repeat text")               #The defenition of the command.
@lightbulb.implements(lightbulb.SlashContext)
async def echo(ctx:lightbulb.Context):          #The callback (what happens) of the command. Must be async and inculude ctx:lightbulb.Context
    await ctx.respond(                          #This responds to the message with a new message
        ctx.options.text)                       #ctx is the context of the command and most things fall under it. 'ctx.options' access the options and then whatever the options name is




@plugin.command                                 #Assigning the command to the plugin. This must be either a plugin or BotApp instance followed by .command
@lightbulb.command("ping",                      #The name of the option, MUST be lowercase
                    "pings the bot")            #The description of the option, can be upper case
@lightbulb.implements(lightbulb.SlashContext)
async def ping(ctx:lightbulb.Context):          #The callback (what happens) of the command. Must be async and inculude ctx:lightbulb.Context

    embed = hikari.Embed(                       #This creates an instance of an embed
        "Pong",                                 #This is the title on the embed
        f"The bots ping is {plugin.app.heartbeat_latency*1000:.2f}ms",         #This is the defeninition (small text) of the embed
        color=hikari.Color.from_rgb((255,255,255)))                            #This is the side color of the embed. Must be a hex code, which is where hikari.Color.from_rgb((r,g,b)) converts it to
    
    embed.set_footer(datetime.datetime.now())                                  #Sets the embeds footer to the current day and time
    
    await ctx.respond(embed=embed)             #Sends the embed. Either context or embed must be filled
