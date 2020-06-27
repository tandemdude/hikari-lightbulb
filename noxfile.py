import nox
import os

PATH_TO_PROJECT = os.path.join(".", "handler")


@nox.session(python=["3.8"])
def format_fix(session):
    session.run("pip", "install", "-U", "black")
    session.run("python", "-m", "black", PATH_TO_PROJECT)


@nox.session(python=["3.8"])
def format(session):
    session.run("pip", "install", "-U", "black")
    session.run("python", "-m", "black", PATH_TO_PROJECT, "--check")
