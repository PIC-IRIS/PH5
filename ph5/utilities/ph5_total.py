#!/usr/bin/env pnpython3
#
#   Find total size of ph5 files in a directory.
#
import os, sys, re

PROG_VERSION = "2014.273"


def main():
	masterRE = re.compile ("master\.ph5")
	
	files = os.listdir ('.')
	S = 0
	F = {}
	B = {}
	M = {}
	biggest = 0
	smallest = 2 ** 64
	for f in files :
		if f[-4:] != '.ph5' : continue
		sz = os.path.getsize (f)
		S += sz
		if masterRE.match (f) :
			F[f] = sz
		else :	
			if sz > biggest :
				biggest = sz
				B = {}
				B[f] = sz
				
			if sz < smallest :
				smallest = sz
				M = {}
				M[f] = sz
	
	if S == 0 :
		print "No ph5 files found."
		sys.exit ()
		
	print "Total: {0} GB,\t".format (S / 1024. / 1024. / 1024.),
	f = F.keys ()[0]
	print "Master: {0}: {1} MB,\t".format (f, F[f] / 1024. / 1024.),
	b = B.keys ()[0]
	print "Largest: {0}: {1} MB,\t".format (b, B[b] / 1024. / 1024.),
	m = M.keys ()[0]
	print "Smallest: {0}: {1} MB.".format (m, M[m] / 1024. / 1024.)


if __name__ == '__main__' :
	main()
	
