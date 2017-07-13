/*   firfilt_py.c   */
/*
 *   Decimate in the time domain. Borrowed from Jim Fowlers firfilt.c.
 *
 *   Steve Azevedo, May 2010
 */
 
#define PROG_VERSION "2013.261.a"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "fir.h"

/*
 *   dfacts -> decimation factors comma separated, 2,4,5
 *   dptr   -> pointer to original data
 *   nsamp  -> number of samples in original data
 *   dtout  -> decimated data
 *   nsampo -> number of samples in decimated data
 *
 *   returns number of samples to shift in time
 */
int
firfilt (char *dfacts, double *dtr, int nsamp, double **dtout, int *nsampo)
{
   int i, j, k, decflg, decm[5], dect, nfltr[5], nfltr2[5], nb[5] ;
   static int sampo;
   int ne[5], ftflg, nshift, ndec, io, nsampf, nte, ntb, neu, nbu;
   double *fltr[5], fscale[5], *bfltr, *efltr, *dtpr, *dtemp, *dto ;
   
   decflg = sampo = 0;
   /*   Parse dfacts here   */
   j = 1;
   decm[0] = (int) atol (dfacts);
   for (i = 0; i < strlen (dfacts); i++) {
      if ((dfacts[i]) == ',') {
         decm[j] = (int) atol (dfacts+i+1);
         j++; i++;
      }
   }
   ndec = j;
   /* get filters */
   for (j = 0; j < ndec; j++) { 
      nfltr[j] = 0;
      for (i = 0; i < NUMDEC; i++) {
         if (decm[j] == filter[i].dec) {
            if ((j < ndec-1) || (filter[i].flag == 0)) {
               nfltr[j] = filter[i].numint;
               fltr[j] = filter[i].fltrp;
            }
         }
      }

      /* see if error */
      if (nfltr[j] == 0) {
         fprintf(stderr, "\n Error: Improper decimation factor = %d \n", decm[j]);
         exit(-1);
      }

      /* calculate scale factor of filter */
      fscale[j] = 0.;
      for (i = 0; i < nfltr[j]; i++) {
         fscale[j] += *(fltr[j]+i);
      }
   }
   /* get buffers for beginning and end padding */
   nte = 0;
   ntb = 0;
   for (j = ndec-1; j > -1; j--) {
      nfltr2[j] = nfltr[j]/2;
      nb[j] = nfltr2[j]+decm[j]*ntb;
      ne[j] = nfltr2[j]+decm[j]*nte;

      ntb = nb[j];
      nte = ne[j];
   }
   if ((bfltr = (double *)calloc(nb[0], sizeof(*bfltr))) == NULL) {
      fprintf(stderr, "\n Error: Allocating memory \n");
      exit(1);
   }
   if ((efltr = (double *)calloc(ne[0], sizeof(*efltr))) == NULL) {
      fprintf(stderr, "\n Error: Allocating memory \n");
      exit(1);
   }

   /* set actual buffer sizes used */
   nbu = nb[0];
   neu = ne[0];
   nshift = 0;   /* clear shift value */
   /* initialize padding to zero */
   for (i = 0; i < nbu; i++) {
      *(bfltr+i) = 0;
      *(efltr+i) = 0;
   }
   ftflg = 0;   /* set first time flag */
   if (ftflg == 0) {
      ftflg = 1;
      /* get space for processing array */
      if ((dtpr = (double *)calloc(nsamp+nb[0]+ne[0], sizeof(double))) == NULL) {
            fprintf(stderr, "\n Error: Allocating memory \n");   
            exit(1);
      }

      /* get space for final answer array */
      if ((dto = (double *)calloc(nsamp+nb[0]+ne[0], sizeof(double))) == NULL) {
         fprintf(stderr, "\n Error: Allocating memory \n");   
         exit(1);
      }
      /* fill processing array */
      for (i = 0; i < nbu; i++) {
         *(dtpr+i) = *(bfltr+i);
      }

      for (i = 0; i < nsamp; i++) {
         *(dtpr+i+nbu) = *(dtr+i);
      }
      
      for (i = 0; i < neu; i++) {
         *(dtpr+i+nbu+nsamp) = *(efltr+i);
      }
      /* filter the trace */
      nsampf = nsamp+nbu+neu;
      for (j = 0; j < ndec; j++) {
         sampo = 0;
         dect = decm[j];
         if (decflg == 1)
            dect = 1;

         for (i = nfltr2[j]; i < nsampf-nfltr2[j]; i += dect) {
            *(dto + sampo) = 0.;
            for (k = 0; k < nfltr[j]; k++) {
               *(dto + sampo) += *(dtpr+i+nfltr2[j]-k)*(*(fltr[j]+k));
            }
            *(dto + sampo) = *(dto + sampo)/fscale[j];
            //printf ("%f\n", *(dto + sampo));
            sampo++;
         }
         if (j == 0)
            io = i;
               
         nsampf = sampo;

         /* switch the array pointers */
         dtemp = dto;
         dto = dtpr;
         dtpr = dtemp;
         /* now do it again */
      }
      /* switch the array pointers back for output*/
      
      dtemp = dto;
      dto = dtpr;
      dtpr = dtemp;
      
      /* get total decimation factor */
      dect = 1;
      if (decflg != 1) {
         for (j = 0; j < ndec; j++) {
            dect = dect*decm[j];
         }
      }   
      /*   ***   Do we need to shift the start time?   ***   */
      //free (dtout);
      //free (dtpr);
      
      dect = 1;   /* calculate total decimation */
      for (j = 0; j < ndec; j++) {
         dect = dect*decm[j];
      }
      if (((nsamp-nshift)%dect) != 0) {
         /* calculate new shift value */
         nshift = dect-((nsamp-nshift)%dect);
         nbu = nb[0]-nshift;   /* get buffer size */
         neu = ne[0];
      } else {
         nshift = 0;
         nbu = nb[0];
         neu = ne[0];
      }
      /* get prebuffer */
      for (i = 0; i < nbu; i++) {
         *(bfltr+i) = *(dtr+nsamp+i-nbu);
      }
   }
   *nsampo = (int) sampo;
   *dtout = (double *) dto;
   /*   debug   */
   //nsampoptr = (int *) nsampo;
   //dtoutptr = (double *) dtout;
   //j = *nsampo;
   //for (i = 0; i < j; i++) {
      //printf ("%f\n", (float) dtout[i]);
   //}
   /*   debug   */
   free (bfltr); free (efltr);
   free (dtpr);

   return (nshift);
}
/*
#include <math.h>
void
main ()
{
   //void *dtout;
   //   To hold the data out pointer and sampo
   //uint32_t dtout, sampo;
   double *dtout;
   int sampo;
   int i, samp_shift;
   double r, val[36000];
   double *d;
   
   for (i = 0; i < 36000; i++) {
      r = (double) i * (M_PI / 180.);
      val[i] = sin (r);
   }
   //   Decimate by a factor of 2 X 4 X 5 = 40
   //   36000 sample sine wave in val
   sampo = 0; dtout = NULL;
   samp_shift = firfilt ("2,4,5", val, 36000, &dtout, (int *) &sampo);
   fprintf (stderr, "Samples to shift in time: %d\n", samp_shift);
   fprintf (stderr, "Samples out: %d\n", sampo);
   for (i = 0; i < sampo; i++) {
      printf ("%f\n", dtout[i]);
   }
}
*/