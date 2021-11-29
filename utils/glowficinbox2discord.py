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
imap.login(config['glowfic-imap']['username'], config['glowfic-imap']['password'])
status, messages = imap.select("INBOX")
try:
    assert messages[0] is not None
except AssertionError:
    sys.exit(0)
message_len = int(messages[0].decode('utf8'))
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
            if isinstance(subject, bytes) and encoding is not None:
                # if it's a bytes, decode to str
                subject = subject.decode(encoding)
            # decode email sender
            From, encoding = decode_header(msg.get("From"))[0]
            if isinstance(From, bytes) and encoding is not None:
                From = From.decode(encoding)
            if From != "Glowfic Constellation <glowfic.constellation@gmail.com>":
                continue
            To = str(decode_header(msg.get("To"))[0][0])
            if "+" not in To:
                imap.store(str(i), '+FLAGS', '\\Deleted')
                continue
            for part in msg.walk():
                # extract content type of email
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                body = ''
                try:
                    # get the email body
                    body = part.get_payload(decode=True).decode()
                except:
                    pass
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    # print text/plain emails and skip attachments
                    url = "http"+body.split("http")[1].split("\r\n\r\n")[0]
                    notifications.append((int(To.split("+")[1].split("@")[0]), f"{subject}\n{url}"))
                    imap.store(str(i), '+FLAGS', '\\Deleted')
imap.expunge()
imap.close()
imap.logout()
# print(notifications)
if not len(notifications):
    sys.exit(0)

client = discord.Client(chunk_guilds_at_startup=None, guild_subscriptions=False, intents=None)
# token from https://discordapp.com/developers
token = config['discord']['botToken']

Ans = None

@client.event
async def on_ready():
    for notification in notifications:
        try:
            await (await client.fetch_user(notification[0])).send(notification[1])
        except Exception as e:
            print(e)
    await client.close()
    pass

client.run(token)
