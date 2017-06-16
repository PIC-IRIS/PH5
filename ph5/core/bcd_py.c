/*   bcd_py.c   */
/*
 *   BCD conversion
 *   Steve Azevedo, April 2014
 */
 
#define PROG_VERSION "2014.119"
 
#include <stdio.h>

/*   Max and Min for 32 bit number   */
/*
int MAX_32 = 2147483647;
int MIN_32 = -2147483648;
*/

/*
 *   start in nibbles into buffer
 *   len in BCD digits to decode
 */
int
rd_bcd (unsigned char *buf, int start, int len)
{
    int i, ret = 0;
    
    for (i = start; i < start + len; i++) {
        int digit = i & 1 ? buf[i >> 1] & 0x0F : buf[i >> 1] >> 4;
        if (digit > 9) {
            ret = ret * 16 + digit;   /*   Base sixteen   */
        } else {
            ret = ret * 10 + digit;   /*   Base ten       */
        }
            //return 0;
    }
    return ret;
}
