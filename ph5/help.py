# A help file for ph5. When the user types $ ph5, 
# this will print a list of all available commands, 
# along with a brief description.
#
# The dictionary defined in entry_points also 
# contains the entry points fpor each script, 
# for use in setup.py.

# Dave Thomas, 2019-06-11

from __future__ import (print_function)

PROG_VERSION = '2019.162'

from entry_points import CommandList


def main():

	command_list = CommandList()

	descriptions = {group: [ep.get_description_str() for ep in eps]
                    for group, eps in command_list.entrypoints.items()}

	## print (descriptions)

	guis = descriptions['gui_scripts']
	consoles = descriptions['console_scripts']

	print (" ")
	print ("************************************************")
	print ("These are the available PH5 scripts and commands.")
	print ("************************************************")

	print (" ")
	print ("GUI Scripts:")
	print ("Use Help menu for detailed instructions for each.")
	print ("-------------------------------------------------")
	for item in sorted(guis):
		print (item)

	print (" ")
	print ("Console Scripts:")
	print ("Type command_name -h for detailed instructions for each.")
	print ("-------------------------------------------------")
	for item in sorted(consoles):
		print (item)


if __name__ == '__main__':
    main()
