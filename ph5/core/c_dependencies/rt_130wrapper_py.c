/*   rt_130wrapper_py.c   */

/*
 *   Parse selected rt-130 packets and contents. (The stuff thats too slooow 
  *  in native python.)
 *
 *   Steve Azevedo, October 2008
 */

#define PROG_VERSION "2010.242" 
 
#include "Python.h"
#include "numpy/arrayobject.h"
#include "rt_130_py.h"

extern void parse_packet_header (unsigned char *, PacketHeader *);
extern void parse_data_header (unsigned char *, DataHeader *);
extern void parse_int16 (uint8_t *, int32_t *, int);
extern void parse_int32 (uint8_t *, int32_t *, int);
extern int parse_steim1 (uint8_t *, int32_t *, size_t, int32_t *, int32_t *);
extern int parse_steim2 (uint8_t *, int32_t *, size_t, int32_t *, int32_t *);
extern int rd_bcd (unsigned char *, int, int);

/*   Initialize   */
/*
PyObject *
rt_130_init (PyObject *self, PyObject *args)
{

  return Py_BuildValue ("");

}
*/

/*   */
PyObject *
rt_130_parse_packet_header (PyObject *self, PyObject *args)
{
  const char *buf;	  /*   Converted packet buffer   */
  Py_ssize_t len;	  /*   Length of converted buffer   */ 
  PyObject *input;	  /*   Input packet buffer   */
  PacketHeader ph;	  /*   Packet header   */
  
  if (! PyArg_ParseTuple (args, "O", &input))
    return NULL;
  
  if (PyObject_AsCharBuffer (input, &buf, &len) != 0)
	return NULL;
  
  parse_packet_header ((unsigned char *) buf, &ph);
  
  return Py_BuildValue ("siiiiiiiiii",  ph.packet_type,
                                        ph.experiment_number,
                                        ph.year,
                                        ph.unit_id_number,
                                        ph.doy,
                                        ph.hh,
                                        ph.mm,
                                        ph.ss,
                                        ph.ttt,
                                        ph.byte_count,
                                        ph.packet_sequence);

}

/*   */
PyObject *
rt_130_parse_data_header (PyObject *self, PyObject *args)
{
  const char *buf;
  Py_ssize_t len;
  PyObject *input;
  DataHeader dh;	/*   Data header   */
  
  if (! PyArg_ParseTuple (args, "O", &input))
    return NULL;
	
  if (PyObject_AsCharBuffer (input, &buf, &len) != 0)
	return NULL;
    
  parse_data_header ((unsigned char *) buf, &dh);
  
  return Py_BuildValue ("iiiiii", dh.event_number,
                                  dh.stream_number,
                                  dh.channel_number,
                                  dh.samples,
                                  dh.flags,
                                  dh.data_format);

}

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

/*   */
PyObject *
rt_130_parse_int16 (PyObject *self, PyObject *args)
{
  const char *buf;	  /*   Converted packet buffer   */
  int num;		  /*   num -> number of samples, len -> packet buffer length   */
  Py_ssize_t len;
  int32_t *data;	  /*   Converted data   */
  PyObject *input;	  /*   Input packet buffer   */
  
  if (! PyArg_ParseTuple (args, "Oi", &input, &num))
    return NULL;
	
  if (PyObject_AsCharBuffer (input, &buf, &len) != 0)
	return NULL;
    
  data = (int32_t *) malloc (sizeof (int32_t) * num);
  if (data == NULL)
    return PyErr_NoMemory ();
    
  parse_int16 ((uint8_t *) buf, data, num);
  
  return PyTuple_FromArray (data, num);

}

/*   */
PyObject *
rt_130_parse_int32 (PyObject *self, PyObject *args)
{
  const char *buf;
  int num;
  Py_ssize_t len;
  int32_t *data;
  PyObject *input;
  
  if (!PyArg_ParseTuple (args, "Oi", &input, &num))
	return NULL;
	
  if (PyObject_AsCharBuffer (input, &buf, &len) != 0)
	return NULL;
	
  data = (int32_t *) calloc (num, sizeof (int32_t));
  if (data == NULL)
	return PyErr_NoMemory ();
	
  parse_int32 ((uint8_t *) buf, (int32_t *) data, num);
  
  return PyTuple_FromArray (data, num);

}

/*   */
PyObject *
rt_130_parse_steim1 (PyObject *self, PyObject *args)
{
  const char *buf;
  int num, ret;
  Py_ssize_t len;
  int32_t *data, x0, xn;
  PyObject *input;
  
  if (! PyArg_ParseTuple (args, "Oi", &input, &num))
	return NULL;
	
  if (PyObject_AsCharBuffer (input, &buf, &len) != 0)
	return NULL;
	
  data = (int32_t *) calloc (num + 2, sizeof (int32_t));
  if (data == NULL)
	return PyErr_NoMemory ();
	
  ret = parse_steim1 ((uint8_t *) buf, data, num, &x0, &xn);
  if (ret != 0) {
	fprintf (stderr, "Warning: Steim1 raw data decompression error. Data from RefTek packet garbled.\n");
  }
  data[num] = x0; data[num + 1] = xn;
  //printf ("C %ld %ld\n", x0, xn);
  /*   Dec Ref???   */
  //buf = NULL;
  return PyTuple_FromArray (data, num + 2);

}

/*   */
PyObject *
rt_130_parse_steim2 (PyObject *self, PyObject *args)
{
  const char *buf;
  int num, ret;
  Py_ssize_t len;
  int32_t *data, x0, xn;
  PyObject *input;
  
  if (! PyArg_ParseTuple (args, "Oi", &input, &num))
	return NULL;
	
  if (PyObject_AsCharBuffer (input, &buf, &len) != 0)
	return NULL;  
	
  data = (int32_t *) calloc (num + 2, sizeof (int32_t));
  if (data == NULL)
	return PyErr_NoMemory ();
	
  ret = parse_steim2 ((uint8_t *) buf, data, num, &x0, &xn);
  if (ret != 0) {
	fprintf (stderr, "Warning: Steim2 raw data decompression error. Data from RefTek packet garbled.\n");
  }
  data[num] = x0; data[num + 1] = xn;
  /*   Dec Ref???   */
  //buf = NULL;
  return PyTuple_FromArray (data, num + 2);

}

/*   */
PyObject *
rt_130_bcd2int (PyObject *self, PyObject *args)
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
  //printf ("%d, %d, %d\n", start, num, ret);
  //
  
  //free (buf);
  
  return Py_BuildValue ("i", ret);

}

static PyMethodDef rt_130methods[] = {
  { "get_packet_header", rt_130_parse_packet_header, METH_VARARGS, "Parse an rt-130 packet header and return the contents." },
  { "get_data_header", rt_130_parse_data_header, METH_VARARGS, "Parse an rt-130 data packet header and return the contents." },
  { "read_int16", rt_130_parse_int16, METH_VARARGS, "Parse two byte rt-130 data and return in an array." },
  { "read_int32", rt_130_parse_int32, METH_VARARGS, "Parse four byte rt-130 data and return in an array."},
  { "read_steim1", rt_130_parse_steim1, METH_VARARGS, "Parse steim1 compressed data from an rt-130 data packet."},
  { "read_steim2", rt_130_parse_steim2, METH_VARARGS, "Parse steim2 compressed data from an rt-130 data packet."},
  { "bcd2int", rt_130_bcd2int, METH_VARARGS, "Pass in a char buf in BCD and return an int"},
  { NULL, NULL, 0, NULL } 
};

PyMODINIT_FUNC
initrt_130_py (void)
{
  (void) Py_InitModule ("rt_130_py", rt_130methods);
}
