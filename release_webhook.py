import os

import requests

import lightbulb

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
