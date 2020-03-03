# Hotwords

Hotwords is the generic mechanism for customizing Fletcher behavior on a server. This will allow a server admin to do various creature features, but for now it enables responding to a hotword regex with a reaction.

## Permissions
This feature requires the *Read Messages* and *Add Reactions* permissions.

## Configuration

Configuration is a JSON blog under the key `hotwords`

```
{
    "target_emoji": "newspaper2",
    "regex": "^.*newspaper *please.*$",
    "insensitive": "true" # Omit if case sensitive
}
```
