# Bridging Channels

Bridging two channels means that Fletcher sends any message sent in one to the other, and vice versa (unless the bridge is unidirectional). To bridge channels, Fletcher must have the correct permissions (most relevantly, `Send Messages` and `Manage Webhooks`).

## Bridge Configuration
 To bridge a channel, send `!bridge servername:channelname`, in the channels you want bridged to each other.

 To demolish a bridge, send `!demolish` on both sides. 

## Three+-way bridges
 Bridging more than two channels together is possible. To bridge three channels, creating a median between the three, you can:
#### In channel #sync-a
```
!bridge sync-b
!bridge sync-c
```

#### In channel #sync-b
```
!bridge sync-a
!bridge sync-c
```

#### In channel #sync-c
```
!bridge sync-a
!bridge sync-b
```

## Permissions
Discord-Discord sync requires the *Read Messages*, *Read Message History*, and *Manage Webhooks* permissions on both servers.

For a full discussion of the permissions that Fletcher requires, see [Permissions granted via the OAuth screen](permissions.md).

## Fletcher Configuration
In each server configuration file, set the `synchronize` preference to `on`. Fletcher must be reloaded or restarted for these changes to take effect (this happens automatically every 15 minutes).

Configuration example: this is a fletcherrc configuration entry for a server that has synchronization scanning on.

```
[Guild 000000000000000001]
synchronize = on
```
## Expected behavior
In a bridged channel, message edits will be respected and transferred, and replies will be bridged (viewable as embeds of the message link from the other side of the bridge). However, message deletions currently are not bridged.

