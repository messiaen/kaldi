#!/bin/bash

awk '/J=[0-9]+\s+S=[0-9]+\s+E=[0-9]+\s+W=.*\s+v=-?[\.0-9]+\s+a=-?[\.0-9]+\s+l=-?[\.0-9]+/ {
        split($7, parts, "=", seps)
        ll=parts[2]
        print $1 "\t" $2 "\t" $3 "\t" $4 "\t" $5 "\t" $6 "\t" $7 "\ts=" 0.0
        next
}
/.*/ {print $0}'
