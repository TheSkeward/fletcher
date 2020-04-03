Text manipulators

##Rot13
**Syntax:** `!rot13 message`

Replaces the message with a [ROT13](https://en.wikipedia.org/wiki/ROT13) version. React with :rot13: or 🕜 to receive a DM with the original message.

##Spoiler
`!spoiler` or `!memfrob`

**Syntax:** `!spoiler message`

Similar functionality to !rot13, but obfuscates the message more thoroughly and works with all characters (not just alphabetic ones). React with 🙈 to receive a DM with the original message.

##Scramble
**Syntax:** `!scramble` as a comment on an uploaded image

Replaces image with a deep fried version. React with 🔎 to receive a DM with the original image.

##Mobilespoil
**Syntax:** `!mobilespoil` as a comment on an uploaded image

Re-uploads image using Discord's spoiler function, and deletes original message.

##MD5
**Syntax:** `!md5 message`

Provides an [MD5](https://en.wikipedia.org/wiki/MD5) hash of the message text (does not work on images).

##Blockquote 
####Quote previous message
**Syntax:** `!blockquote`

Creates a blockquote of your previous message using a webhook embed. Webhooks have a higher character limit than messages, so this allows multiple messages to be combined into one.

####Quote multiple previous messages
**Syntax:** `!blockquote <<n (title)`

**Example:** `!blockquote <<3 Hamlet's Soliloquy`

Creates a blockquote from your past *n* messages, with optional title. The example would produce a quote from your past 3 messages, titled "Hamlet's Soliloquy".

####Quote from message text
**Syntax:** `!blockquote message`


####Quote from message links
**Syntax:** `!blockquote messagelink1 (messagelink2) (...)`

Creates a blockquote from one or more linked messages.

##Smallcaps
**Syntax:** `!smallcaps message`

Gives message in sᴍᴀʟʟᴄᴀᴘs.

##Smoltext
**Syntax:** `!smoltext message`

Gives message in ˢᵘᵖᵉʳˢᶜʳᶦᵖᵗ.

##Zalgo
**Syntax:** `!zalgo message`

Gives message z̴̴ͭa̴̴̳l̴̴̑g̴̴̺o̴̴̅҉̴̴̭'d.

##OCR
**Syntax:** `!ocr` as a comment on an uploaded image

Extracts text from image. Alternatively, react to an image with 🔏. If you posted the image, the text will be pasted in the channel. Otherwise, you'll receive the text in a DM.
