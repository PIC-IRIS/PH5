/*   rt_130_py.h   */
/*
 *   Steve Azevedo, October 2008
 */
 
#define HEADER_VERSION "2010.241"

#include <stdint.h>
#include <string.h>

#define rdb(dest, buf) \
    (dest) = (uint8_t) *(buf);

#define rdstr(dest, buf, len) { \
    memcpy((void *) dest, (void *) buf, (size_t) len); \
    dest[len] = '\0'; \
}

#define rdchr(dest, buf) \
    dest = (char) *(buf);
    
#define rdint(dest, buf, len) { \
    char temp[10]; \
    memcpy ((void *) temp, (void *) buf, (size_t) len); \
    temp[len] = '\0'; \
    dest = (int32_t) atoi (temp); \
}

#define rdb_int16(dest, buf) { \
    (dest) = (int16_t) ((buf)[0] << 8 | (buf)[1]); \
}

#define rdb_uint32(dest, buf) { \
    (dest) = ((uint32_t)((uint8_t *)buf)[0]<<24 | (uint32_t)((uint8_t *)buf)[1]<<16 | (uint32_t)((uint8_t *)buf)[2]<<8 | (uint32_t)((uint8_t *)buf)[3]) ; \
}

#define rdb_int32(dest, buf) { \
    (dest) = ((int32_t)((uint8_t *)buf)[0]<<24 | (uint32_t)((uint8_t *)buf)[1]<<16 | (uint32_t)((uint8_t *)buf)[2]<<8 | (uint32_t)((uint8_t *)buf)[3]) ; \
}

#define get_int8(buf) \
    ((int8_t)((int8_t *)buf)[0])

#define get_uint8(buf) \
    ((uint8_t)((uint8_t *)buf)[0])
    
#define get_uint16_be(buf) \
    ((uint16_t)((uint8_t *)buf)[0]<<8 | \
     (uint16_t)((uint8_t *)buf)[1])

#define get_uint32_be(buf) \
    ((uint32_t)((uint8_t *)buf)[0]<<24 | \
     (uint32_t)((uint8_t *)buf)[1]<<16 | \
     (uint32_t)((uint8_t *)buf)[2]<<8 | \
     (uint32_t)((uint8_t *)buf)[3])

#define get_int16_be(buf) \
    ((int16_t)get_uint16_be(buf))

#define get_int32_be(buf) \
    ((int32_t)get_uint32_be(buf))
    
/*   XXX   */
typedef struct packet_header {
    char packet_type[3];
    uint8_t experiment_number;
    uint16_t year;
    uint16_t unit_id_number;
    uint16_t doy;
    uint8_t hh;
    uint8_t mm;
    uint8_t ss;
    uint16_t ttt;
    uint16_t byte_count;
    uint16_t packet_sequence;
} PacketHeader ;

typedef struct data_header {
    uint16_t event_number;
    uint8_t stream_number;
    uint8_t channel_number;
    uint16_t samples;
    uint8_t flags;
    uint8_t data_format;
} DataHeader ;

