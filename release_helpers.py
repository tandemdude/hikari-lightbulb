import os
import sys
import re

import lightbulb

version_regex = re.compile(r"__version__\s*=\s*\"\d+\.\d+\.\d+\"")

if len(sys.argv) < 2:
    print("No command provided")
    sys.exit(0)

command = sys.argv[1]
if command == "send_webhook":
    import requests
    requests.post(
        os.environ["RELEASE_WEBHOOK"],
        json={
            "embeds": [
                {
                    "title": f"Lightbulb v{lightbulb.__version__} released to PyPi.",
                    "description": f"Install with:\n```pip install -U hikari-lightbulb=={lightbulb.__version__}```\n[Changelog](https://hikari-lightbulb.readthedocs.io/en/latest/changelogs/v2-changelog.html#version-{lightbulb.__version__.replace('.', '-')})",
                }
            ]
        },
    )
    print("Webhook sent")
elif command == "bump_version":
    version_parts = lightbulb.__version__.split(".")
    version_parts[-1] = str(int(version_parts[-1]) + 1)
    new_version = ".".join(version_parts)

    with open("lightbulb/__init__.py") as fp:
        content = fp.read()
        new_content = version_regex.sub(f"__version__ = \"{new_version}\"", content)

    with open("lightbulb/__init__.py", "w") as fp:
        fp.write(new_content)
    print(f"Updated version from {lightbulb.__version__} to {new_version}")
else:
    print(f"Command {command} not recognised")
