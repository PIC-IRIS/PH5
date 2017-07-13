/*   ibm2ieeewrapper_py.c   */

 #include "Python.h"
 #include "numpy/arrayobject.h"
 
 extern void ibm2ieee (int *, int *);
 
/* 
PyObject *Convert_Big_Array(long array[], int length)
  { PyObject *pylist, *item;
    int i;
    pylist = PyList_New(length);
    if (pylist != NULL) {
      for (i=0; i<length; i++) {
        item = PyInt_FromLong(array[i]);
        PyList_SET_ITEM(pylist, i, item);
      }
    }
    return pylist;
  } 
*/
PyObject *
PyTuple_FromArray (int32_t *values, int num_values)
{
  int i;
  
  PyObject *tuple = PyList_New (num_values);
  if (tuple == NULL)
	return NULL;
  
  for (i = 0; i < num_values; i++)
	PyList_SetItem (tuple, i, PyFloat_FromDouble ((double) values[i]));
  
  if (PyErr_Occurred ())
    return NULL;
  else
    return tuple;
}
 
/*   */
PyObject *
segy_ibm2ieee (PyObject *self, PyObject *args)
{
  uint32_t *buf;
  int num, i;
  //
  PyObject *input, *item;
  //Py_ssize_t len;
  //printf ("Get args...\n");
  if (!PyArg_ParseTuple (args, "Oi", &input, &num))
	return NULL;
	
  buf = (uint32_t *) calloc (num, sizeof (uint32_t));
  //printf ("Read buffer...num: %d\n", num);
  //if (PyObject_AsCharBuffer (input, &buf, &len) != 0)
	//return NULL;
  
  for (i = 0; i < num; i++) {
    item = PySequence_GetItem (input, i);
    if (PyInt_Check (item))
      ;
      //printf ("Is\n");
    buf[i] = (uint32_t) PyInt_AsLong (item);
  }
  //Convert an array of ibm floats to an array of ieee floats	
  ibm2ieee ((int32_t *) buf, (int32_t *) &num);
  
  //Return a tuple of double floats
  return PyTuple_FromArray ((int32_t *) buf, num);

} 
 
static PyMethodDef ibm2ieeemethods[] = {
  { "ibm2ieee", segy_ibm2ieee, METH_VARARGS, "Convert an array of 32 bit IBM floats to IEEE floats."},
  { NULL, NULL, 0, NULL } 
};

PyMODINIT_FUNC
initibm2ieee_py (void)
{
  (void) Py_InitModule ("ibm2ieee_py", ibm2ieeemethods);
}