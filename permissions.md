# Permissions granted via the OAuth screen

## Manage Roles

This is for persistent roles, so that if someone leaves and rejoins the server they automatically get their roles readded (if enabled with Save/Restore Roles Join Behavior).

## Manage Channels

This is required for the `!snooze` and `!part` self-managed permissions system.

## Kick Members

This is required for the `!kick` command, which kicks a user with a message sent to them, with no risk of accidentally deleting their messages from the server..

## Manage Nicknames

The Save/Restore Roles Join Behavior uses this to restore nickname along with roles. As of writing, the two must be granted together.

## Manage Webhooks

This is for the Discord-Discord sync, it's used to scan the list for any webhooks that belong to it.

## Read Messages

Allow triggering commands in channels. Read messages is vital.

## Send Messages

Without this, the bot can only respond in PMs, which breaks notably teleports.

## Manage Messages

Spoilers are autoremoved using this permission. Also, if the bot is in `snappy` mode, then command triggers get removed in a few other places including teleports.
Lets it delete webhook messages which is vital if the Discord-Discord sync gets used.

## Embed Links

Needed for teleports and most functionality involving messages.

## Attach Files

Used for !scramble ing images and message previews.

## Read Message History

Link previews depend on this to scan history for the message in question. Discord-Discord sync requires it for old message edits.

## Add Reactions

Many functions react to their own messages so folks can easily respond without having to search for emoji. Not strictly necessary, but !spoiler and !rot13 get harder to use.

## Use External Emojis

Used for the rot13 unspoil button, and in future other buttons.
