Terms used and actions explained:
"interface" or "Fletcher interface" refers to the settings available upon logging into https://fletcher.fun. Settings for individual servers are found by clicking on the relevant icon in the sidebar. Fletcher reciprocity settings are found by clicking the icon with the two arrows in the sidebar.
To set a preference, DM Fletcher the relevant `!preference` command.
Preferences may take up to 15 minutes to come into effect.

## Configurable Preferences in Fletcher
  Preferences configurable with !preference.

## Bookmarking etc. functionality
  Fletcher can be integrated wtih Trello via the `!trello login` command.
[ao3 bookmark function seems to not be working]

## Discord threads
  With the command `!preference use_threads True` Fletcher will auto-add you to threads in channels you are in. As a mod, you can also (on the interface) add yourself to the `manual-mod-userslist` for that server and be automatically added to threads created in that server. You can also set `create-thread` as a `bridge-function` for a channel, and then all posts posted in that channel will automatically create threads (useful for event announcement channels).

## Fletcher reciprocity
  To opt out of Fletcher reciprocity entirely, you can set `!preference reciprocity False`. If you are a mod and would like to specifically opt in people on your server, you can set the `reciprocity` preference to `True` in the Fletcher interface. To block or blacklist, use the commands `!preference reciprocity-blacklist` and `!preference reciprocity-blocklist`. You can block individual people or servers by using their IDs (developer mode needs to be turned on to access these), comma separated. Blacklisting will make blacklisted users, or users who only share a blacklisted server with you, invisible to you. Blocklisting will make you invisible to blocklisted users or users you only share a blocklisted server with. 

## Hotwords
  Fletcher hotword functionality allows Fletcher to DM you when a specific word (such as your name) is mentioned. You can set it individually for a server, by sending the below command there and replacing `hotword` with a word of your choosing, or set them globally by DMing Fletcher the same.
```!preference hotwords {"dm-me-on-mention": {"dm_me": 1, "regex": "hotword", "insensitive": "true"}}```
This command operates off of regular regex syntax, so you can set multiple hotwords or multiple different categories of hotwords. For example, the below preference would create 2 categories of hotwords, "name" and "interest". You'd receive DMs for both name1 and name2, interest1 and interest2. 
```{"name": {"dm_me": 1, "regex": "name1|name2", "insensitive": "true"}, "interest": {"dm_me": 1, "regex": "interest1|interest2", "insensitive": "true"}}```

