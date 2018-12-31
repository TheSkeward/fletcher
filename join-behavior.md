# Join Behaviors
## Lockout
[Issue #12](https://todo.sr.ht/~nova/fletcher/12)

This behavior consists of removing permissions from users who join a guild, sending them a message with information about the rules (currently limited to 2000 characters due to message splitting and technical limitations), and requiring them to agree to it. If they do not answer before the configured timeout, they are automatically kicked.

Configuration example: this is a fletcherrc configuration entry for a guild that requires agreement to "Be nice, don't do crimes." If this is not agreed to in 3600.00 seconds, the user is kicked and the process starts over the next time they join.

```
[Guild 000000000000000001]
on_member_join = lockout
lockout_message = Be nice, don't do crimes.
lockout_timeout = 3600.00
```
 
## Randomize Role (aka CRAB)
[Issue #50](https://todo.sr.ht/~nova/fletcher/50)

This behavior consists of assigning a role out of a list of one or more roles to each member joining a server. Randomness is *not* cryptographically secure, as it uses the building `random` library. Configuration tip: to get a role ID without too much trouble, set the role to pingable, and use the syntax `\@role` to return a message that contains the role's ID rather than the display name.

Configuration example: this is a fletcherrc configuration entry for a guild that has two roles to pick between when members join.

```
[Guild 000000000000000001]
on_member_join = randomize_role
randomize_role_list = 000000000000000001,000000000000000001
```
