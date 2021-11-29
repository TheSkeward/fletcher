import imaplib
import email
from email.header import decode_header
import configparser
import discord
import os
import sys

FLETCHER_CONFIG = os.getenv('FLETCHER_CONFIG', './.fletcherrc')

config = configparser.ConfigParser()
config.read(FLETCHER_CONFIG)
imap = imaplib.IMAP4_SSL("localhost")
imap.login(config['inbound-imap']['username'], config['inbound-imap']['password'])
status, messages = imap.select("INBOX")
message_len = int(messages[0].decode('utf8'))

filters = {}
for key in [k for k in config['inbound-imap'].keys() if "_filter" in k]:
    if key.split("_")[1] == "from":
        filters[config['inbound-imap'][key]] = {
                "channel": key.split("_")[0],
                "body_filter": ""
                }
    if key.split("_")[1] == "body":
        filters[next(filter(lambda _, v: v['channel'] == key.split("_")[0], config['inbound-imap'].items()), (None))[0]]["body_filter"] = config['inbound-imap'][key]

notifications = []
if not message_len:
    sys.exit(0)
for i in range(message_len, 0, -1):
    # fetch the email message by ID
    res, msg = imap.fetch(str(i), "(RFC822)")
    for response in msg:
        if isinstance(response, tuple):
            # parse a bytes email into a message object
            msg = email.message_from_bytes(response[1])
            # decode the email subject
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                # if it's a bytes, decode to str
                subject = subject.decode(encoding)
            # decode email sender
            From, encoding = decode_header(msg.get("From"))[0]
            if isinstance(From, bytes):
                From = From.decode(encoding)
            if From not in filters.keys():
                imap.store(str(i), '+FLAGS', '\\Deleted')
                continue
            To = decode_header(msg.get("To"))[0][0]
            if "+" not in To or To.split("+")[1].split("@")[0] != filters[From]["channel"]:
                imap.store(str(i), '+FLAGS', '\\Deleted')
                continue
            for part in msg.walk():
                # extract content type of email
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                try:
                    # get the email body
                    body = part.get_payload(decode=True).decode()
                except:
                    body = None
                    pass
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    assert body is not None
                    assert isinstance(body, str)
                    if filters[From]["body_filter"] not in body:
                        imap.store(str(i), '+FLAGS', '\\Deleted')
                        continue
                    if msg.get("X-Google-Group-Id"):
                        body = "--".join(body.split("--")[:-1])
                    # print text/plain emails and skip attachments
                    notifications.append((int(To.split("+")[1].split("@")[0]), f"__{subject}__\n{body}"))
                    imap.store(str(i), '+FLAGS', '\\Deleted')
imap.expunge()
imap.close()
imap.logout()
# print(notifications)
# sys.exit(0)

client = discord.Client(chunk_guilds_at_startup=None, guild_subscriptions=False, intents=None)
# token from https://discordapp.com/developers
token = config['discord']['botToken']

Ans = None

@client.event
async def on_ready():
    for notification in notifications:
        try:
            await client.get_channel(notification[0]).send(notification[1])
        except Exception as e:
            print(e)
    await client.close()
    pass

client.run(token)
