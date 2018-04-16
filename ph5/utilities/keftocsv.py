import csv
import argparse

def get_args():
    parser = argparse.ArgumentParser(
            description='Converts a kef file to csv.',
            usage=('Version: {0} keftocsv --file="kef_file" ')
            )
    parser.add_argument("-f", "--file", action="store",
                        required=True, type=str, metavar="file")
    parser.add_argument("-o", "--outfile", action="store",
                    required=True, type=str, metavar="outfile")
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    f = open(args.file, 'r')
    content = f.readlines()
    kef_dict_list = []
    kef_dict = {}
    fieldnames = []
    for line in content:
        line = line.strip()
        if line.startswith('#'):
            continue
        elif '=' in line:
            field, value = line.split('=')
            kef_dict[field] = value
            if field not in fieldnames:
                fieldnames.append(field)
        elif line.startswith('/'):
            kef_dict = {}
            kef_dict['table'] = line
            if 'table' not in fieldnames:
                fieldnames.append('table')
            kef_dict_list.append(kef_dict)
    print fieldnames
    if kef_dict_list:
        with open(args.outfile, 'wb') as of:  # Just use 'w' mode in 3.x
            w = csv.DictWriter(of, kef_dict_list[0].keys())
            # write headers in same order they were read
            dh = dict((h, h) for h in fieldnames)
            w.fieldnames = fieldnames
            w.writerow(dh)
            w.writerows(kef_dict_list)

if __name__ == "__main__" :
    main()
