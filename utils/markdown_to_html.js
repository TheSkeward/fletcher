const { toHTML } = require('discord-markdown');
const split2 = require('split2');
process.stdin
    .pipe(split2('\0'))
    .on('data', function (line) {
        console.log(toHTML(line));
    })
