/*   rt_130wrapper_py.c   */

/*
 *   Parse selected rt-130 packets and contents. (The stuff thats too slooow 
  *  in native python.)
 *
 *   Steve Azevedo, October 2008
 */

#define PROG_VERSION "2014.119" 
 
#include "Python.h"
#include "numpy/arrayobject.h"

extern int rd_bcd (unsigned char *, int, int);

/*   */
PyObject *
Bcd2int (PyObject *self, PyObject *args)
{
  const char *buf;
  int num, start, ret; 
  Py_ssize_t len;
  PyObject *input;
  
  if (! PyArg_ParseTuple (args, "Oii", &input, &start, &num))
	return NULL;
	
  if (PyObject_AsCharBuffer (input, &buf, &len) != 0)
	return NULL;  
  
  ret = rd_bcd ((unsigned char *) buf, start, num);
  
  return Py_BuildValue ("i", ret);

}

static PyMethodDef bcdmethods[] = {
  { "bcd2int", Bcd2int, METH_VARARGS, "Pass in a char buf in BCD and return an int"},
  { NULL, NULL, 0, NULL } 
};

PyMODINIT_FUNC
initbcd_py (void)
{
  (void) Py_InitModule ("bcd_py", bcdmethods);
}
