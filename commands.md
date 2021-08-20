(A) Requires elevated (admin) privileges.
(S) In snappy mode, prompt is removed for this command. This is configurable behavior per-server.

## Set Preference (`!preference`):
#### 0-args
 Output full config 
#### 1-args/`!man`
 list specific info for 1 command
#### Flag verbose
 list arguments for commands

## Help (`!help`):
#### 0-args
 list all available commands
#### 1-args/`!man`
 list specific info for 1 command
#### Flag verbose
 list arguments for commands

## Issue (`!issue`):
#### 1-args (#)
 show info about an issue in the Fletcher issue tracker (http://fletcher.fun/todo)

## Status (`!status`):
#### 0-args
 print last commit message for current deployed version

## ROT-13 (`!rot13`):
#### varargs
 delete message and replace with ROT-13 flip. Classic spoiler command, especially to preserve spoilers on copy. Prepopulates with :clock1330: reaction.
#### 🕜 (`:clock1330:`, first suggestion when you type 13)
 DMs user with ROT-13 of target message. Does not support embeds.

## Spoiler (`!spoiler`):
#### varargs
 delete message and replace with modified memfrob flip. Newer spoiler command, usable similar to Rot-13, but with improved number and Unicode obfuscation. Prepopulates with :seenoevil: reaction.
#### 🙈 (`:seenoevil:`)
 DM user with modified memfrob flip of target message. Does not support embeds.

## Scramble (`!scramble`):
#### 0-args
 this command requires a picture uploaded by user beforehand, scrambles image reversibly. Does not support GIFs or large images. Prepopulates with `:mag_right:`.
#### 🔎 (`:mag_right:`)
 DM user with unscrambled image.

## (S) Zalgo (`!zalgo`):
#### varargs
 print text with lots of diacritics added. Inspired by eemo.net.

## (S) Blockquote (`!blockquote`):
#### 0-args
 "blockquote" the last message sent by calling user in the channel. Does not include images.
Ex:

```
[11:44] #general <Cain> And you can quote me on that
[11:45] #general <Cain> !blockquote
[11:46] #general <Fletcher>
| And you can quote me on that
| (S) Cain
```

#### 1-args (explicit body text)
 similar to the last, but the quoted text is specified in the same message. If multi-line, note that the text on the first line becomes the title of the embed.
#### 1-args (link)
 take message body from link ( you can get a message link with the :link: reaction or the :bookmark: reaction)
#### 1 or 2-args (history)
 you can create an embed longer than 2000 characters by sending multiple messages before a blockquote for up to 6000 characters.
Ex:

```
[11:44] #general <Cain> Point A: Alpha
[11:45] #general <Cain> Point B: Beta
[11:46] #general <Cain> !blockquote <<2 optionalTitle
[11:47] #general <Fletcher>
| optionalTitle
| Point A: Alpha
| Point B: Beta
| (S) Cain
```

## (S) X-React (`!xreact`):
#### 1 or 2-args (name, number)
 Add a reaction to the last non-self post with the name specified. Works with animated and external emoji. User can then add that reaction, regardless of whether they have Nitro. If more than one react exists with the name specified, the numbers specified as the second argument is added.

## Table it:
#### 🏓 (`:ping_pong:`, first suggestion for table)
 DMs user after 24 hours to ask them to pick up a conversation again. Messages immediately with the content of the target message to save it for later.

## Assemble (`!assemble`):
#### 3-args (short name, users required, long name)
 Creates a banner for triggering collective action when support reaches critical mass. The short name must be one word, no spaces. Usable via `!assemble` or `!canvas`.
Ex

```
[11:44] #general <Cain> !canvas sierra 5 Sierra Roadtrip!
[11:45] #general <Fletcher> Banner created! '!pledge sierra' to commit to this pledge.
```

## Pledge (`!pledge`):
#### 1-args (short name)
 pledge support for a banner when it hits critical mass.
Ex:

```
[12:15] #general <Abel> !pledge sierra
[12:16] #general <Fletcher> You pledged your support for banner sierra (one of 4 supporters). It needs 1 more supporter to reach its goal.
[12:17] #general <Baker> !pledge sierra
[12:18] #general <Fletcher> Critical mass reached for banner sierra! Paging supporters: @Cain, @David, @Ellie, @Abel, @Baker. Now it's up to you to fulfill your goal :)
```

## Defect (`!defect`):
#### 1-args (short name)
 the reverse of pledge. Once critical mass is reached, the command is disabled, though. This command might be useful in DMs.

## Banners (`!banners`):
#### 0-args
 lists currently active banners. Note that banners are global, not server-specific.
Ex:

```
[11:00] #general <Cain> !banners
[11:01] #general <Fletcher> Banner List:
EA READING GROUP for reading if goal of 5 members is reached
1 supporter · goal is 5
MADE: 2018-12-06 01:12 (1 week ago)
—————
DC Dinner 119 Dinner party in January? Tentatively hosted in Rockville
5 supporters · goal is 4
MADE: 2018-12-12 15:28 (yesterday)
MET: 2018-12-12 15:32 (yesterday)
```

## Teleport (`!teleport`):
#### 1 or 2-args (target, description)
 messages the current channel, then the target channel, then edits both messages with direct jump links to each other channel at that point in history. This helps when scrolling back in history when a conversation moves or splits among channels. Target is either a channel name or a server name: channel name pair – for example, to teleport from server Aleph, channel general to server Gamma, channel particular, the command should be `!teleport Gamma:particular` sent in Aleph #general.

## Message ID (`!message`):
#### 1-args (ID)
 converts a message ID to a full link. Useful if you "Copy ID" for a message and want to provide a link to that message in conversation. The message must be on the server this command is called on.

## Preview (`!preview`):
#### 1-args (ID or link)
 copies the content of a specified message (selected by ID or link) and reproduces it with attribution. If link expansion is enabled on a server, then this happens automatically for links. Note that copying a message with images, originally (posted in a channel marked as ~~(18)~~, causes the images to be linked rather than embedded inline if the target is not marked ~~(18)~~).

## Bookmark (`!bookmark`):
#### 🔖 (:bookmark:)
 DMs the user a link to the current place in conversation, along with a message preview.
#### 🔗 (:link:)
 same as 🔖 without message preview. Useful for getting a message link for copy on mobile.

## Paste (`!paste`):
#### 0-args
 sends a message to the channel with the last message DMed by Fletcher to the calling user. This is often used in conjunction with 🔗 (:link:) to paste the last copied link.

## Math (`!math` or `!latex`):
#### 1-args (mathexpression)
 render math in LaTeX format. mathexpression is wrapped in $$.

## Moderator Report (`!modreport`):
#### 0 or 1-args (message to mods)
 message mod(s) on duty. See admin documentation for details on configuring who this message is sent to.
#### 👁 🗨 (`:eye_in_speech_bubble:`)
 same as above but auto-removed to make semi-anonymous, even if Fletcher is not configured snappy.

## Part (`!part`):
#### 1-args (target channel)
 causes user to be permanently removed from a channel.

## Snooze (`!snooze`):
#### 0,1,2-args (target, hours)
 causes user to be removed for 24 hours or specified length of time for target channel.

## UwU (`!uwu`):
#### 0-args
 vanity command to uwu at the bot. Works via DM and reaction as well.

## Pick (`!pick`):
#### 1-args (choices)
 pick one of the comma-separated choices
#### 2-args (# of choices)
 pick ## of the comma-separated choices
Ex:

```
[11:45] #general <Cain> !pick 2 of apple banana, cherry, durian
[11:46] #general <Fletcher> I'd say banana, cherry.
```

## Roll (`!roll`):
#### #d sides
 roll some dice and show statistics with results.

## Shindan (`!shindan`):
#### 1-args (link)
 display information about a Shindan quiz. prepopulates a 📛 reaction.
#### 📛 (`:name_badge:`)
 run Shindan with your username.

## SCP (`!scp`):
#### 1-args (ID or link)
 display information about an SCP.

## Retrowave (`!retrowave`):
#### line1 / line2 / line3
 create a retroimage with three lines as specified. To center, surround with / /. Note that slashes should have spaces around them, or they may be ignored.

## Twilestia (`!twilestia`):
#### 0-args
 prints a random Celestia×Twilight Sparkle image

## Danbooru (`!dan`):
#### 1+-args (tag tag ...)
 prints a random image from Danbooru with the given tag(s). If channel is a DM or a SFW channel, an implicit rating:safe is added to the search.

## GitHub Report (`!ghreport`):
Ex:

```
!ghreport Title of issue
Body Text
```

Report an issue to the repository associated with this server.

## GitHub Search (`!ghsearch`):
#### 1-args (query)
 search associated chat repository for issues with specified query.

## Kick (`!kick`):
#### 1-args (reason for kick)
 Kicks user from server, and DMs them a reason. Does not delete any of the user's messages.
## Mobilespoil (`!mobilespoil`):
 Spoilers images while on mobile. Preface message with image with `!mobilespoil`.
#### 📳 (`:vibration_mode:`)
 Spoilers an image sent when used as a reaction.

## OCR (`!ocr`):
 Pastes the text in an image using optical character recognition.
#### 🔏 (`:lock_with_ink_pen:)
 DMs user the OCR of an image.

## Reminders (`!remindme`):
 Sets a reminder for a specified time.

Ex:

```
[12:08] #general <Cain> !remindme in 3 days 2 hours 5 minutes check messages
[12:08] #general <Fletcher> Setting a reminder at NOW() + '3 days 2 hours 5 minutes'::interval
| check messages
```

## MD5 (`!md5`):
 Provides an MD5 (https://en.wikipedia.org/wiki/MD5) hash of the message content.

## Smallcaps (`!smallcaps`):
 Provides a smallcaps version of the message content.

## Smoltext (`!smoltext`):
 Provides a smoltext (superscript) version of the message content.

## Bigemoji (`!bigemoji`):
 Sends a larger version of an emoji.

## Avatar (`!pfp` or `!avatar`):
 Sends the profile picture of a mentioned user, or if no user is mentioned, sends the profile 
 picture of the sender.

## Role color (`!rolecolor` or `!rolecolour`):
 Recolors a role if the user has the permissions to do so, with the format `!rolecolor role_name   hexcode`.

## Notification of message reacts:
#### 📡 (`:satellite:`)
 When used to react to a message, notifies the user whenever a new react is added to the message.

## Markdown of a message:
#### #️⃣  (`:hash:`)
 DMs user the markdown of a message.

## Archive links:
#### 📁 (`:file_folder:`)
 Archives links in a message.

## List users (`!names`):
 Lists the display names of all users currently in a channnel (and on the other side of a bridge, if the channel is bridged).

## Next new moon (`!nextnewmoon`):
 Displays the date of the next new moon.

## Next full moon (`!nextfullmoon`):
 Displays the date of the next full moon.

## On this day (`!onthisday`):
 Provides significant events that happened on the current date in history.

## Inspire (`!inspire`):
 Sends an AI-generated inspirational image from https://inspirobot.me.

## My color (`!mycolor` or `!mycolour`):
 Tells you your current role color.


## Color (`!color @user`)
 Tells you a mentioned user's role color.

## XKCD (`!xkcd`): 
 Sends the daily XKCD comic.

## Delete a Fletcher post:
#### ❌ (`:x:` or `:deletethispost:`)
 Some Fletcher messages (e.g. linked message previews) can be deleted using this react.

## Animal image commands (`!fox`, `!dog`, `!pupper` or `!possum`):
 Sends a random image of the animal in the command. 

## Bubblewrap (`!bubblewrap`):
 Sends digital "bubblewrap".

## Copy emoji (`!copy_emoji` or `!esteal`):
 Lets you take an emoji from another fletcher-enabled server.

## Fling (`!fling`)
 Sends `(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧` plus whatever text the user puts after.

## Current time (`!now` or `!time`):
 Tells you the current time. Defaults to America/New_York if the user hasn't set a timezone.

## Pin messages:
#### 📍 (`:round_pushpin:`)
 Pins a message if the user has the right permissions.

## Translate (`!translate`):
 Translates from one language to another.

Ex:
```
[10:42] <Cain> !translate en fr hello
[10:42] <Fletcher> Translating...
[10:43] <Fletcher> Bonjour
```

## Thingiverse (`!thing`):
 Sends a Thingiverse page (desired search term needs to be followed with `query`).

## Image stylize (`!stylish`):
 Stylizes an image sent with the command with the style `wave`, `mosaic`, `candy`, or `pencil`.

## Rank (`!rank`):
 Displays the user's or a mentioned user's rank and corresponding element and wikidata object.

## Lesbaru (`!lesbaru`):
 Sends a lesbian subaru forester ad.

## Help (`!help` or `!man`):
 Sends a command list and descriptions.

## Privacy (`!privacy`):
 Provides information about Fletcher's privacy policy.

## Preferences (`!preference`):
 Allows you to set a number of preferences.

## LIFX (`!lifx`):
 Lets users change the colors of each other's LIFX bulbs.

## Ace Attorney (`!ace`):
 Makes messages into an ace-attorney style courtroom scene given a message ID for starting point.

## Channel log (`!chanlog`): 
 Takes a log of the channel a user does it in if they have admin permissions.

## Memo (`!memo`):
 Stores a memo under the name the user sets it as.

Ex:
```
[10:27] <Cain> !memo work submit work on May 25th
[10:27] <Fletcher> submit work on May 25th
[12:15] <Cain> !memo work
[12:15] <Fletcher> submit work on May 25th
```

## Clickbait (`!clickbait`):
 Sends an AI-generated clickbait title.

## Glowfic site status (`!glowup`):
 Tells the user whether the Glowfic site is up.

## Glowfic notifications (`!glownotify`):
 Lets the user receive notifications for updates to Glowfic threads.

## Wikipedia (`!wiki`):
 Searches Wikipedia for whatever text the user includes with the command.


## Channel topic (`!topic`):
 Tells the user the topic of the channel they're currently in.

## Add role (`!roleadd` or `!addrole`): 
 Adds a role to the server if the user has the correct permissions.

## Delete role (`!roledel` or `!delrole`):
 Deletes a role from the server if the user has the correct permissions.

## Mod ping (`!modping`):
 Pings a role as a mod.

## Last active channel (`!lastactive_channel` or `!lastactivity_channel`):
 Displays the last active channel in a server.

## Last active user (`!lastactive_user` or `!lastactivity_user`):
 Displays the last active user.

## Slow mode (`!cooldown` or `!slowmode`):
 Sets a cooldown time for the channel if the user has the correct permissions.

## Bridge channels (`!bridge server_name:channel_name`):
 Bridges channels between servers.

## Copy permissions (`!copy_permissions_from`):
 Copies permissions from another channel.

## Open role (`!openrole`):
 Assigns a role to every user who reacts.

## Invite (`!invite`):
 Sends a channel invite to a specified user.

## Delete invites (`!delete_all_invites`):
 Deletes all active invites for a server.

## Lockout (`!lockout`):
 Lockout or reset a user's permissions.

## Voice opt-out (`!voiceoptout`):
 Leaves all voice channels for a server.

## Channel invite request (`!requestinvitechannel`):
 Makes the reacts to a channel invite message send an invitation request to the user, who can approve or disapprove them.

## Role assignment (`!revoke` or `!assign`):
 Revokes or assigns a role for a mentioned user.

## Open channel (`!openchannel`): 
 Automatically adds anyone who reacts to the channel invite message.

## Trello (`!trello`):
 Allows user to utilize some Trello functionalities, `!login trello` to access.

## Amulet (`!amulet` or `!amulet_filter`):
 Checks if a poem is an amulet (https://text.bargains/amulet/).

## Food (`!food`):
 Sends a random rotating food from https://archive.org/download/rotatingfood.

## Kaomoji (`!kao sadness/joy/love/indifference`):
 Sends a random kaomoji within the specified category along with the text the user includes after it.

## Two Stats (`!2stats`):
      Pulls 2 stats from the list at https://twostats.neocities.org/.
