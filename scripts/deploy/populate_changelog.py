import argparse

CHANGE_LOCATION_MARKER = "<!-- next-changelog -->\n"

parser = argparse.ArgumentParser()
parser.add_argument("new_changes_path")
parser.add_argument("changelog_path")


def main(new_changes_path: str, changelog_path: str) -> None:
    with open(new_changes_path) as fp:
        new_changes = fp.read().strip()

    with open(changelog_path) as fp:
        changelog_contents = fp.read()

    if CHANGE_LOCATION_MARKER not in changelog_contents:
        raise RuntimeError("cannot find location to place changelog")

    new_changes = f"{CHANGE_LOCATION_MARKER}\n{new_changes}\n\n----\n"
    changelog_contents = changelog_contents.replace(CHANGE_LOCATION_MARKER, new_changes)

    with open(changelog_path, "w") as fp:
        fp.write(changelog_contents)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.new_changes_path, args.changelog_path)
