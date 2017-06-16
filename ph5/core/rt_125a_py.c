/*   rt_125a_py.c   */

#include <stdint.h>
#include <string.h>
#include <stdio.h>

void
cvt24to32 (uint8_t *ibuf, int32_t *data, int num)
{
    unsigned char *pt, p1, p2, p3;
    int i, offset;    
    //printf ("num: %d\n", num);
    //printf ("int32: %d long int: %d" , sizeof (int32_t), sizeof (long int));
    for (i = 0; i < num; i++) {
        /*   Get each of the 3 bytes and shift them into place   */
        offset = i * 3;
        pt = ibuf + offset;
        p1 = *pt; p2 = *(pt + 1); p3 = *(pt + 2);
        //data[i] = 0x0;
        data[i] = (p1 << 16) + (p2 << 8) + p3;
        //printf ("Not corrected: %d\n", data[i]);
        /*   Extend sign bit   */
        if (p1 & 0x80)
            data[i] -= 0x1000000;
            
        //printf ("Sign corrected: %d\n", data[i]);
    }
}