#!/bin/bash
echo "Making test PH5!"
cd ph5/test_data/
mkdir ph5
cd ph5
initialize_ph5 -n master.ph5
segdtoph5 -n master.ph5 -U 13N -r ../segd/3ch.fcnt
130toph5 -n master.ph5 -r ../rt130/2016139.9EEF.ZIP
125atoph5 -n master.ph5 -r ../rt125a/I2183RAW.TRD
metadatatoph5 -n master.ph5 -f ../metadata/station.xml
mstoph5 -n master.ph5 -d ../miniseed/
keftoph5 -n master.ph5 -k ../metadata/array_8_130.kef
keftoph5 -n master.ph5 -k ../metadata/array_9_rt125a.kef
keftoph5 -n master.ph5 -k ../metadata/experiment.kef
resp_load -n master.ph5 -a 1,8,9 -i ../metadata/input.csv
echo "Finished creating test PH5"








