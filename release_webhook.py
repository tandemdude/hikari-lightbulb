import requests
import os
import lightbulb


requests.post(
    os.environ["RELEASE_WEBHOOK"],
    json={
        "embeds": [{
            "title": f"Lightbulb v{lightbulb.__version__} released to PyPi.",
            "description": f"Install with:\n```pip install -U hikari-lightbulb=={lightbulb.__version__}",
        }]
    }
)
