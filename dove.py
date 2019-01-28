"""pydove - a simple python bulk mailer

Usage:
  dove.py --config=<file> --recipients=<file> --message=<file> <subject>
  dove.py (-h | --help)
  dove.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  -c <file> --config=<file>      configuration YAML file
  -r <file> --recipients=<file>  recipients CSV file
  -m <file> --message=<file>     message markdown file

"""

import csv
import logging
import os.path as osp
from email import message
from smtplib import SMTP

import markdown
import yaml
from docopt import docopt
from validate_email import validate_email

logger = logging.getLogger(__name__)


class Recipient:
    def __init__(self, name, email, salutation):
        self.name = name
        self.email = email
        self.salutation = salutation


def get_configs(configfile):
    with open(osp.abspath(osp.expanduser(configfile))) as cf:
        configdict = yaml.load(cf)
    return configdict


def get_recipients(csvfile):
    recipients = []
    with open(osp.abspath(osp.expanduser(csvfile))) as csvf:
        reader = csv.DictReader(csvf)
        for row in reader:
            if validate_email(row['email']):
                recipients.append(Recipient(row['name'], row['email'], row['salutation']))
            else:
                logger.warning(f'Invalid email address: {row["email"]} for {row["name"]}')
    return recipients


def prepare_email(mdtext, subject, recipient, sender):
    mdtext = recipient.salutation + '\n\n' + mdtext
    html_content = markdown.markdown(mdtext)
    email_message = message.Message()
    email_message.add_header('From', sender)
    email_message.add_header('To', recipient.email)
    email_message.add_header('Subject', subject)
    email_message.add_header('MIME-Version', '1.0')
    email_message.add_header('Content-Type', 'text/html; charset="utf-8"')
    email_message.set_payload(html_content)
    return email_message

def send_bulk(recipients, mdtext, configs, subject):
    host = configs['smtp']['host']
    port = configs['smtp']['port']
    username = configs['smtp']['username']
    password = configs['smtp']['password']
    for r in recipients:
        email = prepare_email(mdtext, subject, r, configs['mail']['from'])
        server = SMTP(f'{host}:{port}')
        server.ehlo()
        server.starttls()
        server.login(username, password)
        server.send_message(email, configs['mail']['from'], r.email)

def main(args):
    print(args)
    configs = get_configs(args['--config'])
    recipients = get_recipients(args['--recipients'])
    mdtext = ''
    with open(osp.abspath(osp.expanduser(args['--message']))) as mdf:
        mdtext = mdf.read()
    send_bulk(recipients, mdtext, configs, args['<subject>'])


if __name__ == '__main__':
    arguments = docopt(__doc__, version='pydove 0.1')
    main(arguments)
