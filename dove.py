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
from smtplib import SMTP, SMTPHeloError, SMTPNotSupportedError, SMTPException
import time

import jsonschema
import markdown
import yaml
from docopt import docopt
from progress.bar import Bar
from validate_email import validate_email

logger = logging.getLogger(__name__)


config_schema = """
type: object
properties:
  smtp:
    type: object
    required: [host, port, username, password]
    properties:
      host:
        type: string
      port:
        type: number
      username:
        type: string
      password:
        type: string
      throttle:
        type: number
  mail:
    type: object
    required: [from, test_email]
    properties:
      from:
        type: string
      test_email:
        type: string
"""

class Recipient:
    def __init__(self, name, email, salutation):
        self.name = name
        self.email = email
        self.salutation = salutation


def get_configs(configfile):
    with open(configfile) as cf:
        configdict = yaml.safe_load(cf)
    schema = yaml.safe_load(config_schema)
    try:
        jsonschema.validate(instance=configdict, schema=schema)
        return configdict
    except jsonschema.ValidationError as ve:
        logger.error('bad config file',ve)
        return None

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
    mdtext = recipient.salutation + ' ' + recipient.name + '\n\n' + mdtext
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
    if 'throttle' in configs['smtp']:
        throttle = configs['smtp']['throttle']
    else:
        throttle = 1.0
    bar = Bar('Processing', max=len(recipients))
    server = SMTP(f'{host}:{port}')
    try:
        server.starttls()
        server.login(username, password)
        for r in recipients:
            email = prepare_email(mdtext, subject, r, configs['mail']['from'])
            server.send_message(email, configs['mail']['from'], r.email)
            logger.info(f'Sent email to {r.name} ({r.email})')
            bar.next()
            time.sleep(throttle)
    except SMTPException as err:
        logger.error('SMTP error: ', err)
    except RuntimeError as err:
        logger.error('SSL runtime error: ', err)
    finally:
        server.close()
        bar.finish()

def main(args):
    cfg_path = osp.abspath(osp.expanduser(args['--config']))
    if not osp.exists(cfg_path):
        logger.error(f'path: {cfg_path} does not point to an existing file.')
        return
    configs = get_configs(cfg_path)
    if not configs:
        return
    rcp_path = osp.abspath(osp.expanduser(args['--recipients']))
    if not osp.exists(rcp_path):
        logger.error(f'path: {rcp_path} does not point to an existing file.')
        return
    recipients = get_recipients(rcp_path)
    msg_path = osp.abspath(osp.expanduser(args['--message']))
    if not osp.exists(msg_path):
        logger.error(f'path: {msg_path} does not point to an existing file.')
        return
    mdtext = ''
    with open(msg_path) as mdf:
        mdtext = mdf.read()
    send_bulk(recipients, mdtext, configs, args['<subject>'])


if __name__ == '__main__':
    arguments = docopt(__doc__, version='pydove 0.1')
    main(arguments)
