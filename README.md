# Fletcher: A Discord Moderation Bot.
Copyright (C) 2020 Novalinium <fletcher@noblejury.com> (Noble Jury Software)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

## Description
Fletcher is a message bot that aims to resolve common moderation tasks in
Discord, a popular chat platform. It is designed to be scalable, easy to run,
and secure (e.g. will not interfere with other programs running on the same
host and will not disclose user information inappropriately). 

### Functionality at time of writing includes
- Teleports between channels, including across servers
- One or two way synchronization between channels, including across servers
- Spoiler codes for text (ROT13 [classic] and memfrob [wider character support
  and name obfuscation]) and images
- Channel activity checks
- User activity checks
- Voice channel updates
- Moderation reports (automated and manual)
- Moderation role ping bypass
- Moderation permissions elevation (similar to `sudo`)
- Issue tracker integration
- Management of new server members (role assignment, rules acknowledgement,
  auto role save and restore)
- GitHub integration
### And a few more fun modules
- Collective action coordination
- Music relay
- Math rendering
- Random image posting (Google Photos)
- ShindanMaker integration
- RetroWave Image Generator

## Installation
If you would like to self-host Fletcher, email the author: we'll work something
out. This is a source code release of only the main modules, without optional
modules or other ancillaries provided. Alternatively, simply add the hosted
Fletcher to your own Discord server using the OAuth grant link at
http://fletcher.fun/add.

## Documentation
Documentation for this code is in progress at https://man.sr.ht/~nova/fletcher,
but the author strives to make the code readable without much trouble. This area
is under development. Currently, the bot can self-report loaded commands with
the `!help' command, as well as some additional information with the `verbose'
parameter. In addition, a command flow diagram is included in controlflow.dot,
as well as a PNG (Warning: large file) at
https://novalinium.com/rationality/fletcher.png.

## Development
Development can be tracked via the project issue tracker at
https://todo.sr.ht/~nova/fletcher, and on the author's blog at
https://novalinium.com/blog. Most announcements take place on a Discord that
this bot was built for, email the author if you would like access to the
announcements Discord. Development and hosting costs are generously supported
through Liberapay (https://liberapay.com/novalinium/): it takes time and
resources to support this bot, and Liberapay helps make this possible.

If you have feature requests or would like to contribute to the project,
patches are accepted by email or through the project issue tracker.

## Caveats
Warning! This project DOES NOT provide all files needed to self-host. It is
missing the test harness, as well as the debugging, code injection and SystemD
unit files, as well as any database schemas. This software is *not* General
Data Protection Regulation (EU) 2016/679 compliant on its own, and should be
paired with appropriate log parsing software for compliance. Some functionality
may not be ADA Amendments Act of 2008 compliant due to technologic limitations
and/or limited understanding by the author. Finally, per the terms of the AGPL,
there is NO WARRANTY provided with this program. If you would like a less
restrictive license, please contact the author, and we'll discuss it.
