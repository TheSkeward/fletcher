Terms used and actions explained:
"interface" or "Fletcher interface" refers to the settings available upon logging into https://fletcher.fun.
Settings for individual servers are found by clicking on the relevant icon in the sidebar.
Fletcher reciprocity settings are found by clicking the icon with the two arrows in the sidebar.
To set a preference, DM Fletcher the relevant `!preference` command.
Preferences may take up to 15 minutes to come into effect.
Channel IDs, Server IDs and User IDs are only accessible with Discord Developer Mode turned on.
To set a preference in the Fletcher interface (server-wide), navigate to that server, click `Add Preference` and put the name of the preference (e.g. `preview`) in the Key section, and a value (e.g. `True`, `False`, `on`) in the Value section.

To set a preference in the Fletcher interface (channel-specific), click `Add Section`, put in the Channel ID for the channel you want your preferences to come into effect on, and set a preference the same way you would for a server-wide preference.

## Configurable Preferences in Fletcher
  Preferences configurable with !preference.

## Bookmarking etc. functionality
  Fletcher can be integrated wtih Trello via the `!trello login` command.

  Fletcher bookmarks can be integrated with AO3 bookmarks by DMing Fletcher `!preference ao3-username username` and `!preference ao3-password password`. Using the bookmark react on a message with an AO3 link will now add that fanfic to your AO3 bookmarks.

## Discord threads
  With the command `!preference use_threads True` Fletcher will auto-add you to threads in channels you are in. As a mod, you can also (on the interface) add yourself to the `manual-mod-userslist` for that server and be automatically added to threads created in that server. You can also set `create-thread` as a `bridge-function` for a channel, and then all posts posted in that channel will automatically create threads (useful for event announcement channels).

## Fletcher reciprocity
  To opt out of Fletcher reciprocity entirely, you can set `!preference reciprocity False`. If you are a mod and would like to specifically opt in people on your server, you can set the `reciprocity` preference to `True` in the Fletcher interface. To block or blacklist, use the commands `!preference reciprocity-blacklist` and `!preference reciprocity-blocklist`. You can block individual people or servers by using their IDs, comma separated. Blacklisting will make blacklisted users, or users who only share a blacklisted server with you, invisible to you. Blocklisting will make you invisible to blocklisted users or users you only share a blocklisted server with.

## Hotwords
  Fletcher hotword functionality allows Fletcher to DM you when a specific word (such as your name) is mentioned. You can set it individually for a server, by sending the below command there and replacing `hotword` with a word of your choosing, or set them globally by DMing Fletcher the same.
```!preference hotwords {"dm-me-on-mention": {"dm_me": 1, "regex": "hotword", "insensitive": "true"}}```
This command operates off of regular regex syntax, so you can set multiple hotwords or multiple different categories of hotwords. For example, the below preference would create 2 categories of hotwords, "name" and "interest". You'd receive DMs for both name1 and name2, interest1 and interest2. 
```{"name": {"dm_me": 1, "regex": "name1|name2", "insensitive": "true"}, "interest": {"dm_me": 1, "regex": "interest1|interest2", "insensitive": "true"}}```

## Privacy etc.
  Setting the `preview-allowed` preference to `False` in the Fletcher interface, either server-wide or for a specific channel, will make links to those messages not be previewed by Fletcher when linked in another server. Note that `preview-allowed` is by default `True`.
You can create exceptions to openchannels by setting `!preference warnlist userid=reason, userid2=reason2` etc, or, to delegate your warnlist to someone else, `!preference
warnlist delegate:userid`. To opt out of warnlists, set `!preference warnlist 0=optout`.
Set `!preference verbose_reminders False` if you don't want the confirmation messsages sent by Fletcher when setting a reminder.
