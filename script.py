#!/usr/bin/env python3
"""Deprecated entry point. Use: tcv wordcloud <file> [options]

Install the package first:
    pip install -e .

Then use:
    tcv wordcloud result.json
    tcv dashboard result.json
    tcv --help
"""
import sys

print(
    'script.py is deprecated.\n'
    'Install the package:  pip install -e .\n'
    'Then use:             tcv wordcloud result.json',
    file=sys.stderr,
)

# Fall through to wordcloud for users who haven't migrated yet
from tcv.nlp import ensure_nltk_data
from tcv.commands.wordcloud_cmd import register
import argparse

p = argparse.ArgumentParser()
register(p.add_subparsers()).set_defaults  # ensure subcommand is loaded

# Shim: treat script.py <file> [old opts] as wordcloud command
argv = sys.argv[1:]
new_argv = ['wordcloud']
i = 0
while i < len(argv):
    arg = argv[i]
    if arg in ('--num_words',):
        new_argv += ['-n', argv[i + 1]]; i += 2; continue
    if arg in ('--output_file',):
        new_argv += ['-o', argv[i + 1]]; i += 2; continue
    new_argv.append(arg)
    i += 1

sys.argv = [sys.argv[0]] + new_argv
from tcv.cli import main
main()
