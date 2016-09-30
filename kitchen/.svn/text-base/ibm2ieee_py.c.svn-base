#include <sys/types.h> 
#include <sys/ioctl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <fcntl.h>
#include <sys/file.h>
#include <sys/stat.h>

/*********************************************************************/
/*        ibm2ieee(in_ibm,out_ieee)                                  */
/*********************************************************************/
/*  Routine to convert from ibm float to ieee float
	in_ibm  - pointer to ibm float number
	out_ieee - pointer to sun float for output

* formatting is derived from SIERRASEIS IBM->HOST conversion
*
*	words:	12345678 12345678 12345678 12345678
*	bits:	12345678 90123456 78901234 56789012
*  IBM:		Seeeeeee mmmmmmmm mmmmmmmm mmmmmmmm   1-7-24
*  IEEE:	Seeeeeee emmmmmmm mmmmmmmm mmmmmmmm   1-8-23
*
*  IBM exponent = 2^(eeeeeee) - 64
*  IEEE exponent= 2^(eeeeeeee)- 127
*
* Numerical value:
*                    s    4e-256             s     (e-64)
*  IBM          =  -1  * 2       * .m   =  -1  * 16      * m/(2^24)
*
*                    s    e-127              s    e-127
*  IEEE         =  -1  * 2      * 1.m   =  -1  * 2       * (1.+ m/(2^23))
*
* dao 06july92  take into account the SEGY header (60-words=240 byte).
* courtesy of David Okaya
*/
void
ibm2ieee(u_int32_t *in_ibm, u_int32_t *out_ieee)
{
   struct ibmf  {
	unsigned int is : 1 ;
	unsigned int ie : 7 ;
	unsigned int im : 24 ;
	} ;

   struct sunf  {
	unsigned int ss : 1 ;
	unsigned int se : 8 ;
	unsigned int sm : 23 ;
	} ;

  unsigned int mapi ;
  unsigned int works, worki;
  int  i;
  struct sunf	*sfl ;
  struct ibmf	*ifl ;

  mapi=0x00800000;	/* bits = 0000 0000 8000 0000 0000 0000 0000 0000 */

 
     	works = 0 ;
	worki = *in_ibm ;
	if(worki == 0) {
		*out_ieee = 0 ;
		return ;
	}
	sfl = (struct sunf *) &works ;
	ifl = (struct ibmf *) &worki ;

	sfl->ss = ifl->is ;	/* set sign bit */

	i = ifl->ie ;  /* set exponent */
	i = i - 64 ;
	i = i*4 ;

	while( ((ifl->im)&mapi) == 0) {
		ifl->im = ifl->im << 1 ;
		i-- ;
	}

	i-- ;	/* takecare of hidden bit */
	sfl->se = i + 127 ;
	sfl->sm = ifl->im ;

	*out_ieee = works ;

      
}

/**************************************************************************/
/*           ieee2int(tpr,nsamp,scale)                                    */
/**************************************************************************/
/*   Subroutine to take and IEEE float trace scale it 
	and convert it to 4 byte integer format.
	tpr = pointer to trace header
	nsamp = number of samples in trace
	scal = scale factor for trace

*/
void
ieee2int(char *tpr, int nsamp, float *scale)
{

	float	fval, *fptr ;
	int	i, *iptr, imax ;

	/* set pointers to appropriate places */
	iptr = (int *) (tpr) ;	/* start of data */
	fptr = (float *) (tpr) ;	/* start of data */

	/* get scale factor */
	*scale = 0. ;
	fptr = (float *)tpr ;
	for(i=0 ; i<nsamp ; i++) {

		if((float)fabs(fval) > *scale)
			*scale = (float)fabs(fval) ;
		*fptr = fval ;
		fptr++ ;
	}

	imax = 2147483647 ;   /* 2**31 - 1 */
	fptr = (float *)tpr ;
	iptr = (int *)tpr ;
	for(i=0 ; i<nsamp ; i++,fptr++,iptr++) {

		*fptr = *fptr/(*scale) ;
		*iptr = (int)(*fptr * imax) ;
	}	

}



