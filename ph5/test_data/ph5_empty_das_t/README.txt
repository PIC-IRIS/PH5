This PH5 has das_t of das 3X500 and 1X1111.
Das 1X1111 has been deleted using nuke_table 2019.037. As the result, its das_t has been truncated and created error when running soft_kef_gen.
PR 482 has been created to fix the above error with this PH5 as test data. sort_kef_gen now only give a warning for that case.
The reason that deleting das isn’t added in the test but PH5 is added instead is because nuke_table will be fix to not truncate das_t for deleting table anymore.