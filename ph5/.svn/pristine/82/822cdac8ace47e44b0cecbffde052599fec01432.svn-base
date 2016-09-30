/*   rt_130_py.c   */
/*
 *   Utility functions for dealing with raw rt-130 files.
 *   Steve Azevedo, October 2008 (Big thanks to Steven Golden)
 */
 
#define PROG_VERSION "2010.242"
 
#include "rt_130_py.h"
#include <stdio.h>

/*   Max and Min for 32 bit number   */
/*
int MAX_32 = 2147483647;
int MIN_32 = -2147483648;
*/

/*
 *   start in nibbles
 *   len in BCD digits
 */
int
rd_bcd (unsigned char *buf, int start, int len)
{
    int i, ret = 0;
    
    for (i = start; i < start + len; i++) {
        int digit = i & 1 ? buf[i >> 1] & 0x0F : buf[i >> 1] >> 4;
        if (digit > 9)
            return 0;
        
        ret = ret * 10 + digit;
    }
    return ret;
}

int
rd_int8 (unsigned char *buf)
{
    return ((unsigned char *) buf)[0];
}

int
rd_int16 (unsigned char *buf)
{
    return (int) (((unsigned char *) buf)[0] * 256 + ((unsigned char *) buf)[1]);
}

/*   */
void
parse_packet_header (unsigned char *buf, PacketHeader *packet_header)
{
    rdstr (packet_header->packet_type, buf, 2);
    //memcpy (packet_header->packet_type, "SH", 2);
    //packet_header->packet_type[2] = '\0';
    //printf ("%s\n", packet_header->packet_type);
    packet_header->experiment_number = (uint8_t) rd_bcd (buf, 4, 2);
    packet_header->year = (uint16_t) rd_bcd (buf, 6, 2);
    packet_header->unit_id_number = (uint16_t) rd_int16 (buf + 4);
    packet_header->doy = (uint16_t) rd_bcd (buf, 12, 3);
    packet_header->hh = (uint8_t) rd_bcd (buf, 15, 2);
    packet_header->mm = (uint8_t) rd_bcd (buf, 17, 2);
    packet_header->ss = (uint8_t) rd_bcd (buf, 19, 2);
    packet_header->ttt = (uint16_t) rd_bcd (buf, 21, 3);
    packet_header->byte_count = (uint16_t) rd_bcd (buf, 24, 4);
    packet_header->packet_sequence = (uint16_t) rd_bcd (buf, 28, 4);
}
/*   */
void
parse_data_header (unsigned char *buf, DataHeader *data_header)
{
    data_header->event_number = (uint16_t) rd_bcd (buf, 32, 4);
    data_header->stream_number = (uint8_t) rd_bcd (buf, 36, 2);
    data_header->channel_number = (uint8_t) rd_bcd (buf, 38, 2);
    data_header->samples = (uint16_t) rd_bcd (buf, 40, 4);
    data_header->flags = (uint8_t) rd_int8 (buf + 22);
    data_header->data_format = (uint8_t) rd_int8 (buf + 23);
}
/*   
 *   buf -> pointer to packet sample data. buf = (ibuf + 24)
 *   data -> pointer to pre-allocated returned data buffer
 *   num -> number of samples from data packet header
 */
void
parse_int16 (uint8_t *ibuf, int32_t *data, int num)
{
    uint8_t *buf;
    int i;
    
    buf = ibuf + 24;
    for (i = 0; i < num; i++) {
        int16_t stmp;
        rdb_int16 (stmp, buf + (2 * i));
        data[i] = (int32_t) stmp;
    }
}
/*
 *   buf -> pointer to packet sample data. buf = (ibuf + 24)
 *   data -> pointer to pre-allocated returned data buffer
 *   num -> number of samples from data packet header
 */
void
parse_int32 (uint8_t *ibuf, int32_t *data, int num)
{
    uint8_t *buf;
    int i;
    
    buf = ibuf + 24;
    for (i = 0; i < num; i++) {
        int32_t itmp;
        rdb_int32 (itmp, buf + (4 * i));
        data[i] = (int32_t) itmp;
    }
}
/*
 *   ibuf -> pointer to packet sample data. buf = (ibuf + 64)
 *   data -> pointer to pre-allocated returned data buffer
 *           the last 2 points are x0 and xn, see steim docs.
 *   num -> number of samples from data packet header
 */
int
parse_steim1 (char *ibuf, 
              int32_t *data, 
              size_t num, 
              int32_t *x0, 
              int32_t *xn)
{
    char tempb;   /*   uint8_t?   */
    char *buf;
    int16_t tempw;   /*   uint16_t?   */
    size_t i, j, nr_frame, ww, smp = 0, smp_old = 0;
    uint32_t w0;
    int32_t d0 = 0; 
    int32_t templ;   /*   uint32_t?   */
    
    buf = ibuf + 64;
    /*   Forward integration constant   */
    *x0 = get_int32_be (buf + 4);
    /*   Back integration constant   */
    *xn = get_int32_be (buf + 8);
    data[0] = *x0;
    /*   On first frame we have w0, x0, and xn so start with w3   */
    i = 3;
    
    for (nr_frame = 0; nr_frame < 16; nr_frame++) {
        /*   First 32 bits of frame, 16 2-bit nibbles   */
        w0 = get_int32_be (buf);
        for (j = (15 - i) * 2; i < 16 && smp < num; i++, j -= 2) {
            /*   Two bit code, 01 = 8 bits, 10 = 16 bits, 11 = 32 bits   */
            ww = (w0 >> j) & 3;
#           define store(temp) { \
                if (smp == 0) \
                    d0= (int32_t) temp; \
                else \
                    data[smp] = (data[smp - 1] + (int32_t) temp) & 0xFFFFFFFF; \
                smp++; \
                if (smp > num) { \
                    smp = num; \
                    data[smp] = 0; \
                } \
            }
            
            if (ww == 1) {          /*   4 bytes        */
                tempb = *(buf + i * 4);
                store (tempb);
                tempb = *(buf + i * 4 + 1);
                store (tempb);
                tempb = *(buf + i * 4 + 2);
                store (tempb);
                tempb = *(buf + i * 4 + 3);
                store (tempb);
            } else if (ww == 2) {   /*   2 words        */
                tempw = get_int16_be (buf + i * 4);
                store (tempw);
                tempw = get_int16_be (buf + i * 4 + 2);
                store (tempw);
            } else if (ww == 3) {   /*   1 long word    */
                templ = get_int32_be (buf + i * 4);
                store (templ);
            }
        }
        buf += 64; i = 1;
        if (smp == smp_old)
            break;
            
        smp_old = smp;
#       undef store
    }
    /*
    if (smp < num)
        fprintf (stderr, "Error: Number of samples in packet less than expected.\n");
    */    
    //printf ("Diff: %d\n", (int) (*xn - data[num - 1]));
    return (int) (*xn - data[num - 1]);   /*   Should be 0   */
}
/*
 *   buf -> pointer to packet sample data. buf = (ibuf + 64)
 *   data -> pointer to pre-allocated returned data buffer
 *           the last 2 points are x0 and xn, see steim docs.
 *   num -> number of samples from data packet header
 */
int
parse_steim2 (char *ibuf, 
              int32_t *data, 
              size_t num, 
              int32_t *x0,
              int32_t *xn)
{
    int8_t tempb;   /*   uint8_t?   */
    char *buf;
    //short tempw;   /*   uint16_t?   */
    size_t i, j, nr_frame, ww, smp = 0, smp_old = 0;
    uint32_t w0;
    int32_t d0 = 0; 
    //long int templ;   /*   uint32_t?   */
    
    buf = ibuf + 64;
    /*   Forward integration constant   */
    *x0 = get_int32_be (buf + 4);
    /*   Back integration constant   */
    *xn = get_int32_be (buf + 8);
    data[0] = *x0;
    /*   On first frame we have w0, x0, and xn so start with w3   */
    i = 3; 
    
    for (nr_frame = 0; nr_frame < 16; nr_frame++) {
        w0 = get_int32_be (buf);
        for (j = (15 - i) * 2; i < 16 && smp < num; i++, j -= 2) {
            ww = (w0 >> j) & 3;
#           define store(temp) { \
                if (smp == 0) \
                    d0 = (int32_t) temp; \
                else \
                    data[smp] = (data[smp - 1] + (int32_t) temp) & 0xFFFFFFFF; \
                smp++; \
                if (smp > num) { \
                    smp = num; \
                    data[smp] = 0; \
                } \
            }
            
            if (ww == 1) {          /*   Four 8 bit differences   */
                tempb = get_int8 (buf + i * 4);
                store (tempb);
                tempb = get_int8 (buf + i * 4 + 1);
                store (tempb);
                tempb = get_int8 (buf + i * 4 + 2);
                store (tempb);
                tempb = get_int8 (buf + i * 4 + 3);
                store (tempb);
            } else if (ww == 2) {   /*   30, 15, or 10 bit differences   */
                unsigned int index = (unsigned int) (((uint8_t *)buf)[i * 4] >> 6);   /*   dnib   */
                uint32_t tmp0 = get_uint32_be (buf + i * 4) & 0x3FFFFFFFU; 
                if (index == 1) {   /*   Single 30 bit difference   */
                    const uint32_t c = 1U << (30 - 1);
                    int32_t tmpl = (int32_t)(-(tmp0 & c) | tmp0);
                    store (tmpl);
                } else if (index == 2) {   /*   Two 15 bit differences   */
                    const uint32_t c = 1U << (15 - 1);
                    uint32_t tmp1;
                    int32_t tmp2;
                    tmp1 = tmp0 >> 15;
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1);
                    store (tmp2);
                    tmp1 = tmp0 & 0x7FFF;
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1);
                    store (tmp2);
                } else if (index == 3) {   /*   Three 10 bit differences   */
                    const uint32_t c = 1U << (10 - 1);
                    uint32_t tmp1;
                    int32_t tmp2;
                    tmp1 = tmp0 >> 20;
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1);
                    store (tmp2);
                    tmp1 = tmp0 >> 10 & 0x3FF;
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1);
                    store (tmp2);
                    tmp1 = tmp0 & 0x3FF;
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1);
                    store (tmp2);
                }
            } else if (ww == 3) {   /*   Five 6 bit, six 5 bit, or seven 4 bit differences    */
                unsigned int index = (unsigned int) (((uint8_t *) buf)[i * 4] >> 6);   /*   dnib   */
                uint32_t tmp0 = get_uint32_be (buf + i * 4) & 0x3FFFFFFFU;
                if (index == 0) {   /*   Five 6 bit differences   */
                    const uint32_t c = 1U << (6 - 1);
                    uint32_t tmp1;
                    int32_t tmp2;
                    tmp1 = tmp0 >> 24;
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                    tmp1 = tmp0 >> 18 & 0x3F; 
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                    tmp1 = tmp0 >> 12 & 0x3F; 
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                    tmp1 = tmp0 >> 6 & 0x3F;  
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                    tmp1 = tmp0 & 0x3F;
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                } else if (index == 1) {   /*   Six 5 bit differences   */
                    const uint32_t c = 1U << (5 - 1);
                    uint32_t tmp1; 
                    int32_t tmp2;
                    tmp1 = tmp0 >> 25;
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                    tmp1 = tmp0 >> 20 & 0x1F; 
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store(tmp2);
                    tmp1 = tmp0 >> 15 & 0x1F; 
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                    tmp1 = tmp0 >> 10 & 0x1F; 
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                    tmp1 = tmp0 >> 5 & 0x1F;  
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                    tmp1 = tmp0 & 0x1F;     
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                } else if (index == 2) {   /*   Seven 4 bit differences   */
                    const uint32_t c = 1U << (4 - 1);
                    uint32_t tmp1; 
                    int32_t tmp2;
                    tmp1 = tmp0 >> 24;     
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1);
                    store (tmp2);
                    tmp1 = tmp0 >> 20 & 0xF; 
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                    tmp1 = tmp0 >> 16 & 0xF; 
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                    tmp1 = tmp0 >> 12 & 0xF; 
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                    tmp1 = tmp0 >> 8 & 0xF;  
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                    tmp1 = tmp0 >> 4 & 0xF;  
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                    tmp1 = tmp0 & 0xF;     
                    tmp2 = (int32_t)(-(tmp1 & c) | tmp1); 
                    store (tmp2);
                }
            }
        }
        buf += 64; i = 1;
        if (smp == smp_old)
            break;
            
        smp_old = smp;
#       undef store
    }
    return (int) (*xn - data[num - 1]);   /*   Should be 0   */
}
/*
#include <stdio.h>
#include <stdlib.h>
int
main ()
{
    
    unsigned char buf[1024];
    int i, diff;
    int32_t *data, x0, xn;
    FILE *fh;
    PacketHeader ph;
    DataHeader dh;
    
    fh = fopen ("2010_055_16_40_92E2.ref", "r");
    while (fread (buf, sizeof (char), 1024, fh) == 1024) {
        parse_packet_header (buf, &ph);
        //printf ("Packet_Type %s\n", ph.packet_type);
        if (ph.packet_type[0] == 'D' && ph.packet_type[1] == 'T') {
            parse_data_header (buf, &dh);
            if (dh.event_number == 6 && dh.stream_number == 1 && dh.channel_number == 1) {
            //if (dh.data_format == 0xc0) {
                
                printf ("Event %d Stream %d Channel %d Samples %d type %x\n", dh.event_number, 
                                                                              dh.stream_number, 
                                                                              dh.channel_number, 
                                                                              dh.samples, 
                                                                              dh.data_format);
                
                data = (uint32_t *) malloc (sizeof (int32_t) * dh.samples);
                diff = parse_steim1 (buf, data, dh.samples, &x0, &xn);
                for (i = 0; i < dh.samples; i++) {
                    if (diff != 0)
                        printf ("Error: %d\t", diff);
                        
                    printf ("%d\n", (int) data[i]);
                }    
                free (data);
                //exit (0);
            }
        }
    }
    fclose (fh);
}
*/