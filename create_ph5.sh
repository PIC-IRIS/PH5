#!/bin/bash
echo "Making test PH5!"
rm -rf ph5/test_data/ph5
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
time_kef_gen -n master.ph5 -o ../metadata/time.kef
keftoph5 -n master.ph5 -k ../metadata/time.kef
keftoph5 -n master -k ../metadata/event_t.kef
sort_kef_gen -n master.ph5 -a > ../metadata/sort_t.kef
keftoph5 -n master -k ../metadata/sort_t.kef
geo_kef_gen -n master.ph5 > ../metadata/offset_t.kef
keftoph5 -n master -k ../metadata/offset_t.kef

mkdir samplerate
cd samplerate
mkdir error
keftoph5 -n master.ph5 -k ../../samplerate/all_arrays.kef
keftoph5 -n master.ph5 -k ../../samplerate/Expirement_SampleRate.kef
keftoph5 -n master.ph5 -k ../../samplerate/Receiver_SampleRate.kef
cp master.ph5 error
mstoph5 -n master.ph5 -d ../../samplerate
keftoph5 -n master.ph5 -k ../../samplerate/Das_SampleRate.kef

cd error
mstoph5 -n master.ph5 -r ../../../samplerate/8H.10075..GH1.2012-08-27T23.01.00.ms
keftoph5 -n master.ph5 -k ../../../samplerate/Das_SampleRate_error.kef

cd ../../
mkdir availability
cd availability
keftoph5 -n master.ph5 -k ../../availability/Availability_all_arrays.kef
keftoph5 -n master.ph5 -k ../../availability/Expirement_Availability.kef
keftoph5 -n master.ph5 -k ../../availability/Receiver_Availability.kef
mstoph5 -n master.ph5 -d ../../availability
keftoph5 -n master.ph5 -k ../../availability/Das_Availability.kef

echo "Finished creating test PH5"
