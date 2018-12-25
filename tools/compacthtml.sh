#!/bin/bash

xmllint --noblanks --c14n11 --nodefdtd --format --encode utf-8 - |
    fgrep -v '<?xml' |
    sed 's/<!-- .* -->//g' |
    tr '\n\t' ' '| 
    tr -s ' '
