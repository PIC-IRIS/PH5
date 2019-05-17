/*   mseedwrapper_py.c   */
/*
 *   Wrap Chads libmseed trace group writing routines.
 *
 *   Steve Azevedo, November 2009
 */

#define PROG_VERSION "2015.119"

#include "Python.h"
#include "libmseed.h"
#include <time.h>
#include <stdint.h>

static FILE *OUTFILE     = 0;
static short int VERBOSE = 0;

/*   Define our trace group as global   */
//static MSRecord *MSR      = 0;
static MSTraceGroup *MSTG = 0;
//static MSTrace *MST       = 0;

//static int ISEQNUM        = 1;

static void
record_handler (char *record, int reclen, void *ptr)
{
    if (fwrite (record, reclen, 1, OUTFILE) != 1)
        ms_log (2, "Can't write to output file.\n");
}

/*   Open output file and initialize our MS Trace Group   */
PyObject *
mseed_write_initialize (PyObject *self, PyObject *args)
{
    const char *outfile;
    //fprintf (stderr, "Parse args...\n");
    if (! PyArg_ParseTuple (args, "si", &outfile, &VERBOSE))
        return NULL;
    //fprintf (stderr, "Open output file %s...", outfile);
    if ((OUTFILE = fopen (outfile, "wb")) == NULL) {
        fprintf (stderr, "Open %s failed. %d\n", outfile, errno);
        perror ("Error:");
        return NULL;
    }

    MSTG = mst_initgroup (NULL);
    //MSR = msr_init (NULL);
    //MST = mst_init (NULL);
    //fprintf (stderr, "Py_RETURN_NONE...\n");
    Py_RETURN_NONE;
}

/*   Add each trace to the MS Trace Group   */
PyObject *
mseed_write_pack (PyObject *self, PyObject *args, PyObject *keywds)
{
    /*   Default netcode XX   */
    char *netcode = "XX";
    /*   Default station   */
    char *station = "XXXXX";
    /*   *** Channel required ***   */
    char *channel;
    /*   Default location code is blank   */
    char *loccode      = "";
    /*   *** Require time ***   */
    char *timestr;
    /*   *** Require sample rate ***   */
    double samplerate;
    /*   Default to INT32 input   */
    //int  encoding     = 3;
    /*   Default block size is 1024   */
    //int  reclen       = 1024;
    /*   Default byte order is little endian since most processing is done on
     *   little endian machines
     */
    //int  byteorder    = 0;
    /*   *** Require data samples ***   */
    /*   Input data is in a array object   */
    PyObject *input_data, *item;
    /*   Things that we expect to be passed in using keywords   */
    static char *kwlist[] = {"data",
                             "timestr",
                             "channel",
                             "samplerate",
                             "netcode",
                             "station",
                             "loccode",
                             NULL} ;
    /*   The view into the input_data (above)   */
    //Py_buffer view;
    /*   libmseeed wants an array of 32 bit ints   */
    int32_t *buf;
    //const char *copybuf;
    int n, num_samples;
    //static MSTrace *mst, *mst_ret;
    //mst = mst_init (NULL);
    static MSRecord *msr;
    static MSTrace *mst_ret;
    msr = msr_init (NULL);

    /*   Parse the values using the keywords   */
    if (!PyArg_ParseTupleAndKeywords (args, keywds, "Ossd|sss", kwlist,
                                                                &input_data,
                                                                &timestr,
                                                                &channel,
                                                                &samplerate,
                                                                &netcode,
                                                                &station,
                                                                &loccode))
        return NULL;


    num_samples = PySequence_Length (input_data);
    //printf ("C: %d\n", num_samples);
    buf = (int32_t *) calloc ((size_t) num_samples, sizeof (int32_t));
    if (buf == NULL)
        return PyErr_NoMemory ();

    Py_INCREF (input_data);
    for (n = 0; n < num_samples; n++) {
        item = PySequence_GetItem (input_data, n);
        //Py_INCREF (item);
        buf[n] = (int32_t) PyInt_AsLong (item);
        Py_DECREF (item);
    }
    //fprintf (stderr, "C length: %d %d\n", num_samples, n);

    /*   Fill in MSR here!   */
    strcpy (msr->channel, channel);
    strcpy (msr->network, netcode);
    strcpy (msr->station, station);
    strcpy (msr->location, loccode);
    //MSR->reclen = reclen;
    /*   Hummm...   */
    //MSR->sequence_number = ISEQNUM++;
    /*   MSR->starttime needs to be a hptime_t   */
    msr->starttime = ms_timestr2hptime (timestr);
    /*   Double float   */
    msr->samprate = samplerate;
    //msr->samplecnt += num_samples;
    /*   1 => INT16, 3 => INT32, 10 => STEIM1, 11 => STEIM2   */
    //MSR->encoding = encoding;
    /*   1 => big endian, 0 => little endian   */
    //MSR->byteorder = byteorder;
    /*   Pointer to an array of int_32_t   */
    msr->datasamples = (void *) buf;
    msr->numsamples = msr->samplecnt = num_samples;
    /*   i => integer   */
    msr->sampletype = 'i';
    /*   D => the state of quality control of the data is indeterminate   */
    msr->dataquality = 'D';
    /*   Add this miniseed record to our trace group   */
    mst_ret = mst_addmsrtogroup (MSTG, msr, 0, -1.0, -1.0);
    if (! mst_ret)
        fprintf (stderr, "Failed to mst_addmsrtogroup.\n");

    //fprintf (stderr, "%f End...\n", (float) MST->starttime);
    //free (buf);
    Py_DECREF (input_data);
    msr_free (&msr);
    //free (msr->datasamples);
    //free (msr);

    Py_RETURN_NONE;
}

/*   Write the mini seed file and clean up   */
PyObject *
mseed_write_close (PyObject *self, PyObject *args, PyObject *keywds)
{
    int packedrecords;
    int64_t packedsamples;
    int reclen, encoding, byteorder;
    int flush = 1;

    static char *kwlist[] = {"reclen",
                             "encoding",
                             "byteorder",
                             NULL} ;
    //fprintf (stderr, "Parse Args...\n");
    /*   Require everything   */
    if (!PyArg_ParseTupleAndKeywords (args, keywds, "iii", kwlist,
                                                           &reclen,
                                                           &encoding,
                                                           &byteorder))
        return NULL;
    //fprintf (stderr, "Process traces...\n");
    /*   Pack the tracegroup   */
    packedrecords = mst_packgroup (MSTG, &record_handler, NULL, reclen,
                                   encoding, byteorder, &packedsamples,
                                   flush, VERBOSE, NULL);

    //fprintf (stderr, "Packed: %d Free...\n", packedsamples);
    /*   Free group, do we need a call to ms_readmsr first??   */
    //mst_free (&MSTG);
    mst_freegroup (&MSTG);

    fclose (OUTFILE);

    Py_RETURN_NONE;
}

/*   Define the entry points from python   */
static PyMethodDef mseed_pymethods[] = {
    { "init_mseed", (PyCFunction) mseed_write_initialize, METH_VARARGS, "Initialize mseed creation." },
    { "pack_mseed", (PyCFunction) mseed_write_pack, METH_VARARGS | METH_KEYWORDS, "Pack mseed records." },
    { "close_mseed", (PyCFunction) mseed_write_close, METH_VARARGS | METH_KEYWORDS, "Close mseed file." },
    { NULL, NULL, 0, NULL }
} ;

PyMODINIT_FUNC
initmseed_py (void)
{
    (void) Py_InitModule ("mseed_py", mseed_pymethods);
}
