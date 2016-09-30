#!/usr/bin/env pnpython3
#
#   Convert version 3 ph5 start shell scripts to version 4 ph5
import sys, os, re

RE0 = re.compile (".*Version:.*")
RE1 = re.compile (".*\'pn3\'")
RE2 = re.compile (".*K3.*")
RE3 = re.compile (".*pnpython3")

fh = open (sys.argv[1])

fixed = ''
while True :
    line = fh.readline ()
    if not line : break
    if RE0.match (line) :
        line = "#   Version: 2016.133\n"
    elif RE1.match (line) :
        line = line.replace ("pn3", "pn4")
    elif RE2.match (line) :
        line = line.replace ("K3", "KX")
    elif RE3.match (line) :
        line = line.replace ("pnpython3", "pnpython4")
        
    print line,
    fixed += line
    
sim_ou_nao = raw_input ("Consertar {0}? (sim/nao): ".format (sys.argv[1]))

if sim_ou_nao == 'sim' :
    with open (sys.argv[1], mode='w') as of :
        of.write (fixed)
else :
    print "Skipping"
    
    