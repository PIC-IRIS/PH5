from ph5.core.columns import PH5VERSION as ph5version
import argparse

PROG_VERSION = "2019.149 Developmental"


def main():
    parser = argparse.ArgumentParser(
        description="Get Usage Info for PH5 Subprograms")
    parser.add_argument("n", type=str, nargs="?",
                        default='', help="PH5 subprogram name")

    string = ""

    try:
        args = parser.parse_args()
        # print "arg.ns:", args.n, ", len = ", len(args.n)

        try:
            if len(args.n) == 0:  # no argument provided by user
                showlist()
        except TypeError:
            showlist()

        args.n = args.n.lower()

##        nlen = len(args.n)  # asterisked display of program name
##        if nlen > 0:
##            targlen = 60
##            nstar = (targlen-nlen)/2 - 1
##            print "*" * targlen
##            nstr = "*" * nstar + " " + args.n + " " + "*" * nstar
##            lnstr = len(nstr)
##            if lnstr < targlen:
##                nstr = nstr + "*" * (targlen - lnstr)
##            elif lnstr > targlen:
##                nstr = nstr[0:targlen]
##            print nstr
##            print "*" * targlen
             
        if args.n == "ph5view":  # GUI; tie this list to that in setup.py
            from ph5.clients.ph5view import ph5_viewer
            string = ph5_viewer.ph5_viewer("").description
        elif args.n == "noven":
            string = "TBD"
        elif args.n == "pforma":
            string = "TBD"
        elif args.n == "kefedit":
            string = "TBD"
        elif args.n == "experiment_t_gen":
            string = "TBD"
        elif args.n == "ph5toevt": # clients
            from ph5.clients import ph5toevt
            string = ph5toevt.ph5toevt("").description
        elif args.n == "ph5toms":
            string = "TBD"
        elif args.n == "ph5torec":
            string = "TBD"
        elif args.n == "ph5tostationxml":
            string = "TBD"
        elif args.n == "ph5toexml":
            string = "TBD"
        elif args.n == "125atoph5":  # console
            string = "TBD"
        elif args.n == "130toph5":  # ?
            string = "TBD"
        elif args.n == "cross_check_event_array_data":
            string = "TBD"
        elif args.n == "csvtokef":
            string = "TBD"
        elif args.n == "dumpfair":
            string = "TBD"
        elif args.n == "dumpsgy":
            string = "TBD"
        elif args.n == "fix_3chan_texan":
            string = "TBD"
        elif args.n == "geo_kef_gen":
            string = "TBD"
        elif args.n == "graotoph5":
            string = "TBD"
        elif args.n == "index_offset_t":
            string = "TBD"
        elif args.n == "initialize_ph5":
            string = "TBD"
        elif args.n == "keftocsv":
            string = "TBD"
        elif args.n == "keftokml":
            string = "TBD"
        elif args.n == "keftoph5":
            string = "TBD"
        elif args.n == "load_das_t":
            string = "TBD"
        elif args.n == "meta_data_gen":
            string = "TBD"
        elif args.n == "nuke_table" or args.n == "delete_table":
            string = "TBD"
        elif args.n == "pformacl":
            string = "TBD"
        elif args.n == "ph5_merge_helper":
            string = "TBD"
        elif args.n == "ph5_total":
            string = "TBD"
        elif args.n == "ph5_validate":
            string = "TBD"
        elif args.n == "recreate_external_references":
            string = "TBD"
        elif args.n == "report_gen":
            string = "TBD"
        elif args.n == "reporttoph5":
            string = "TBD"
        elif args.n == "resp_load":
            string = "TBD"
        elif args.n == "seg2toph5":
            string = "TBD"
        elif args.n == "segdtoph5":
            string = "TBD"
        elif args.n == "segytoph5":
            string = "TBD"
        elif args.n == "set_deploy_pickup_times":
            string = "TBD"
        elif args.n == "set_n_i_response":
            string = "TBD"
        elif args.n == "sort_kef_gen":
            string = "TBD"
        elif args.n == "sort_array_t":
            string = "TBD"
        elif args.n == "ph5tokef":
            string = "TBD"
        elif args.n == "time_kef_gen":
            string = "TBD"
        elif args.n == "tabletokef":
            string = "TBD"
        elif args.n == "unsimpleton":
            string = "TBD"
        else:
            print
            print "Usage: ph5 name {subprogram name}"
            if len(args.n) > 0:
                print "The name '{}' is not supported.".format(args.n)
                print "Type ph5 with no arguments to see the full list."

        print args.n + ": " + string

    except ValueError or TypeError:
        showlist()

    print


def showlist():
    string = """
Enter the name of a subprogram to see details,
e.g. type '$ ph5 ph5toevt' to see info for ph5toevt.
Available subprograms:

GUI scripts:
ph5view, noven, pforma, kefedit, experiment_t_gen

CLIENTS:
ph5toevt, ph5toms, ph5torec, ph5tostationxml, ph5toexml

CONSOLE scripts:
125atoph5, 130toph5, cross_check_event_array_data, csvtokef,
geo_kef_gen, graotoph5, index_offset_t, initialize_ph5, keftocsv,
keftokml, keftoph5, load_das_t, meta_data_gen,
delete_table, pformacl,  ph5_merge_helper, ph5_total,
ph5_validate, recreate_external_references, report_gen,
reporttoph5, resp_load, seg2toph5, segytoph5,
set_deploy_pickup_times, set_n_i_response, sort_kef_gen,
sort_array_t, ph5tokef, time_kef_gen, tabletokef, unsimpleton """
    print "\n"
    print "PH5 Version: "+ph5version
    print string
    return


if __name__ == '__main__':
    main()
