![PyPI](https://img.shields.io/pypi/v/hikari-lightbulb)

# Lightbulb
Lightbulb is designed to be an easy to use command handler library that integrates with the 
Discord API wrapper library for Python, Hikari.

This library aims to make it simple for you to make your own Discord bots and provide
all the utilities and functions you need to help make this job easier.

## Installation
Use the package manager [pip](https://pip.pypa.io/en/stable/) to install Lightbulb.

```bash
pip install hikari-lightbulb
```

## Usage
```python
import lightbulb

bot = lightbulb.Bot(token="your_token_here", prefix="!")


@bot.command()
async def ping(ctx):
    await ctx.respond("Pong!")


bot.run()
```

## Issues
If you find any bugs, issues, or unexpected behaviour while using the library, 
you should open an issue with details of the problem and how to reproduce if possible. 
Please also open an issue for any new features you would like to see added.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please try to update tests as appropriate and ensure that documentation is updated if 
you add any features accessible through the public API.

If you use this library and like it, feel free to sign up to GitHub and star the project,
it is greatly appreciated and lets me know that I'm going in the right direction!

## Links
- **License:** [LGPLv3](https://choosealicense.com/licenses/lgpl-3.0/)
- **Repository:** [GitHub](https://github.com/tandemdude/hikari-lightbulb)
- **Documentation:** [ReadTheDocs](https://hikari-lightbulb.readthedocs.io/en/latest/)
