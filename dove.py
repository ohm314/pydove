"""pydove - a simple python bulk mailer

Usage:
  dove.py --config=<file> --recipients=<file> <message>
  dove.py (-h | --help)
  dove.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  -c <file> --config=<file>      configuration YAML file
  -r <file> --recipients=<file>  recipients CSV file

"""
from docopt import docopt


if __name__ == '__main__':
    arguments = docopt(__doc__, version='Naval Fate 2.0')
    print(arguments)