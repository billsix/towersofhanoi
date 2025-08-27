#!/usr/bin/env python3
import argparse
import sys

from termcolor import colored


def main():
    """
    Colorizes characters from standard input based on command-line arguments.
    Usage: <input> | ./colorize.py "char1=color1,char2=color2"
    Example: echo "123" | ./colorize.py "1=blue,2=white,3=red"
    """
    parser = argparse.ArgumentParser(
        description="Colorize characters from piped input.",
        epilog="Example: echo '123' | ./colorize.py '1=blue,2=white,3=red'",
    )
    parser.add_argument(
        "mapping",
        help="A comma-separated string of character-color pairs (e.g., '1=blue,2=white').",
    )
    args = parser.parse_args()

    # Parse the character-color mapping from the command-line argument
    char_map = {}
    for pair in args.mapping.split(","):
        try:
            character, color_name = pair.split("=")
            char_map[character] = color_name
        except ValueError:
            print(
                f"Error: Invalid mapping format: '{pair}'. "
                "Expected 'char=color'.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Read from stdin line by line
    for line in sys.stdin:
        # Process each character and apply color if it's in the map
        output_line = ""
        for char in line:
            if char in char_map:
                output_line += colored(char, char_map[char])
            else:
                output_line += char

        # Print the colorized line to stdout
        sys.stdout.write(output_line)


if __name__ == "__main__":
    main()
