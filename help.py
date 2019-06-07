"""A help file for ph5. When the user types $ ph5, 
this will print a list of all available commands, 
along with a brief description.

The dictionary defined in entry_points also 
contains the entry points fpor each script, 
for use in setup.py.
"""

from __future__ import (print_function)

import entry_points


def main():
	info = entry_points.entrypointinfo()
	guis = info.getinfo('gui_scripts')
	consoles = info.getinfo('console_scripts')
	print ("Descriptions:")
	print (" ")
	print ("GUI Scripts:")
	##print (guis)

	for item in sorted(guis):
		report = item + ": " + guis[item][0]
		print (report)

	print (" ")
	print ("Console Scripts:")
	##	print (consoles)
	for item in sorted(consoles):
		report = item + ": " + consoles[item][0]
		print (report)


if __name__ == '__main__':
    main()
