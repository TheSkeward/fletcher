(S) In snappy mode, prompt is removed for this command. This is configurable behavior per-server.

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
 delete message and replace with ROT-13 flip. Classic spoiler command, especially to preserve spoilers on copy. Prepopulates with :clock1830: reaction.
#### :clock1830: (:clock1830:, first suggestion when you type 13)
 DMs user with ROT-13 of target message. Does not support embeds.

## Spoiler (`!spoiler`):
#### varargs
 delete message and replace with modified memfrob flip. Newer spoiler command, usable similar to Rot-13, but with improved number and Unicode obfuscation. Prepopulates with :seenoevil: reaction.
#### :seenoevil: (:seenoevil:)
 DM user with modified memfrob flip of target message. Does not support embeds.

## Scramble (`!scramble`):
#### 0-args
 this command requires a picture uploaded by user beforehand, scrambles image reversibly. Does not support GIFs or large images. Prepopulates with :mag_right:.
#### :mag_right: (:mag_right:)
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

## Table it (`!table`):
#### :ping_pong: (:ping_pong:, first suggestion for table)
 DMs user after 24 hours to ask them to pick up a conversation again. Messages immediately with the content of the target message to save it for later.

## Assemble (`!assemble`):
#### 3-args (short name, users required, long name)
 Creates a banner for triggering collective action when support reaches critical mass. The short name must be one word, no spaces. Usable via `!assemble` or `!canvas`.
Ex:

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

## Math (`!math`):
#### 1-args (mathexpression)
 render math in LaTeX format. mathexpression is wrapped in $$.

## Moderator Report (`!modreport`):
#### 0 or 1-args (message to mods)
 message mod(s) on duty. See admin documentation for details on configuring who this message is sent to.
#### 👁 🗨 (:eye_in_speech_bubble:)
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
 display information about a Shindan quiz. prepopulates a :name_badge: reaction.
#### :name_badge: (:name_badge:)
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
