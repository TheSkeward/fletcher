# Bridging Channels

Three things are required to set up synchronization: Fletcher must be granted permission to use Discord features on both servers, configured to synchronize both servers, and webhooks must be created such that Fletcher can detect the channels. Note that this can be used for unidirectional sync, and both the input and output server could be the same.

## Permissions
Discord-Discord sync requires the *Read Messages*, *Read Message History*, and *Manage Webhooks* permissions on both servers.

For a full discussion of the permissions that Fletcher requires, see [Permissions granted via the OAuth screen](permissions.md).

## Fletcher Configuration
In the each server configuration file, set the `synchronize` preference to `on`. Fletcher must be reloaded or restarted for these changes to take effect.

Configuration example: this is a fletcherrc configuration entry for a server that has synchronization scanning on.

```
[Guild 000000000000000001]
synchronize = on
```
 
You must also set the `botNavel` key in the main configuration file. If your Fletcher administrator has not provided you with this key, it is probably ƒ.

Configuration example: this is a fletcherrc configuration entry of setting the botNavel.

```
[discord]
botNavel = ƒ
```
 
## Channel Configuration
In this configuration, we will refer to #aleph and #beta on server Guild.

In the settings for #aleph, navigate to Webhooks. Create a webhook with the name `botNavel (ServerName:TargetChannelName)` (i.e. `ƒ (Guild:beta)`). Repeat this for the corresponding channel for the reverse sync. Reload the server, and test that the sync now works.
