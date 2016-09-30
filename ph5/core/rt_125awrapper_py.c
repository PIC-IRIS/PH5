/*   rt_125awrapper_py.c   */

/*
 *   Parse selected portions of rt-125a packets.
 *
 *   Steve Azevedo, June 2010
 */
 
 #define PROG_VERSION "2010.236"
 
 #include "Python.h"
 #include "numpy/arrayobject.h"
 
 extern void cvt24to32 (uint8_t *, int32_t *, int);
 
PyObject *
PyTuple_FromArray (long int *values, int num_values)
{
  int i;
  int32_t *ivalues;
  
  PyObject *tuple = PyList_New (num_values);
  if (tuple == NULL)
	return NULL;
  
  ivalues = (int32_t *) values;
  for (i = 0; i < num_values; i++)
	PyList_SetItem (tuple, i, PyInt_FromLong ((long int) ivalues[i]));
  
  free (values);
  
  if (PyErr_Occurred ())
    return NULL;
  else
    return tuple;
}
 
/*   */
PyObject *
rt_125a_data_decode (PyObject *self, PyObject *args)
{
  const char *buf;
  int num;
  int32_t *data;
  PyObject *input;
  Py_ssize_t len;
  //printf ("Get args...\n");
  if (!PyArg_ParseTuple (args, "Oi", &input, &num))
	return NULL;
  //printf ("Read buffer...num: %d\n", num);
  if (PyObject_AsCharBuffer (input, &buf, &len) != 0)
	return NULL;
  //printf ("Convert buffer...num: %d len: %d\n", num, (int) len);
  data = (int32_t *) calloc (num, sizeof (int32_t));
  if (data == NULL)
	return PyErr_NoMemory ();
  //printf ("Now num: %d\n", num);
  cvt24to32 ((uint8_t *) buf, (int32_t *) data, num);
  //printf ("Done...\n");
  return PyTuple_FromArray ((long int *) data, num);

} 
 
static PyMethodDef rt_125amethods[] = {
  { "data_decode", rt_125a_data_decode, METH_VARARGS, "Decode a packet of 24 bit ints to a list of 32 bit ints."},
  { NULL, NULL, 0, NULL } 
};

PyMODINIT_FUNC
initrt_125a_py (void)
{
  (void) Py_InitModule ("rt_125a_py", rt_125amethods);
}