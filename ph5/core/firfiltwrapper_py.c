/*   firfiltwrapper_py.c   */

#define PROG_VERSION "2013.261"

#include "Python.h"
#include "numpy/arrayobject.h"

extern int firfilt (char *, double *, int, uint32_t *, uint32_t *);

PyObject *
PyTuple_FromArray (int32_t *values, int num_values)
{
  int i;
  
  PyObject *tuple = PyList_New (num_values);
  if (tuple == NULL)
	return NULL;
  
  for (i = 0; i < num_values; i++)
	PyList_SetItem (tuple, i, PyInt_FromLong ((long int) values[i]));
  
  free (values);
  
  if (PyErr_Occurred ())
    return NULL;
  else
    return tuple;
}

PyObject *
run_firfilt (PyObject *self, PyObject *args)
{
  //const char *buf;
  char *dfacts;
  int ionum;
  double *dodata; 
  int i, iinum, samp_shift; 
  int32_t *obuf;
  double *didata, *d;
  PyObject *input, *item;
  /*
   *   input  -> input data to be decimated
   *   iinum  -> number of samples in input
   *   dfacts -> the decimation factors 2, 4, or 5. Up to 5
   *             levels of decimation comma separated.
   */
  //printf ("ParseTuple\n");
  if (! PyArg_ParseTuple (args, "Ois", &input, &iinum, &dfacts))
    return NULL;
    
  //printf ("calloc double\n");
  didata = (double *) calloc (iinum, sizeof (double));
  if (didata == NULL)
    return PyErr_NoMemory ();
    
  //printf ("calloc int32\n");
  obuf = (int32_t *) calloc (iinum, sizeof (int32_t));
  if (obuf == NULL)
    return PyErr_NoMemory ();

  //printf ("Convert to double\n");
  /*   Convert input python list to an array of doubles   */
  for (i = 0; i < iinum; i++) {
    item = PySequence_GetItem (input, i);
    didata[i] = (double) PyInt_AsLong (item);
    Py_DECREF (item);
  }

  //printf ("firfilt\n");
  /*   Decimate the data returning the number of samples to shift in time   */
  samp_shift = firfilt (dfacts, didata, iinum, &dodata, &ionum);
  /*   dodata contains a pointer to the output array   */
  d = dodata;
  for (i = 0; i < ionum; i++)
    obuf[i] = (int32_t) d[i] + 0.5;
    
  //printf ("return\n");
  obuf[ionum] = (int32_t) samp_shift;
  free (didata); free (d);
  return PyTuple_FromArray (obuf, ionum + 1);

}

static PyMethodDef firfiltmethods[] = {
    { "decimate", run_firfilt, METH_VARARGS, "Decimate a timeseries." },
    { NULL, NULL, 0, NULL }
} ;

PyMODINIT_FUNC
initfirfilt_py (void)
{
  (void) Py_InitModule ("firfilt_py", firfiltmethods);
}