import hikari
import lightbulb

bot = lightbulb.BotApp("TOKEN","PREFIX")            #CREATES AN INSTANCE OF THE BOT



bot.load_extensions("extentions.commands")          #LOADS THE EXTENTION. MUST BE A RELATIVE PATH IN A STRING


if __name__=="__main__":
    bot.run()                                       #RUNS THE BOT