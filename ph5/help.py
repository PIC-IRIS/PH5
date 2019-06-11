# A help file for ph5. When the user types $ ph5,
# this will print a list of all available commands,
# along with a brief description.
#
# The dictionary defined in entry_points also
# contains the entry points fpor each script,
# for use in setup.py.

# Dave Thomas, 2019-06-11

from __future__ import (print_function)
from entry_points import CommandList


PROG_VERSION = '2019.162'


def main():

    command_list = CommandList()
    entry_points = []
    for _, eps in command_list.entrypoints.items():
        entry_points.extend([ep for ep in eps])
    commands = {}
    for ep in entry_points:
        if not commands.get(ep.type):
            commands[ep.type] = [ep]
        else:
            commands[ep.type].append(ep)

    print('PH5: PASSCAL HDF5')
    print('')
    print('Usage:')
    print('    <command> [args]')
    for type, ep_list in commands.items():
        if type:
            print('')
            print(type)
            for ep in sorted(ep_list, key=lambda x: x.command):
                print(ep.get_description_str())
    print('')
    print('Type "<command> --help" for more information on a command.')


if __name__ == '__main__':
    main()
