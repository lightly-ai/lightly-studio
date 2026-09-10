import { McapWriter } from '@mcap/core';
import { MessageWriter } from '@foxglove/rosmsg2-serialization';
import { parse } from '@foxglove/rosmsg';
import { compress } from 'lz4js';

const schemaText = `std_msgs/Header header
uint32 height
uint32 width
sensor_msgs/PointField[] fields
bool is_bigendian
uint32 point_step
uint32 row_step
uint8[] data
bool is_dense
================================================================================
MSG: std_msgs/Header
builtin_interfaces/Time stamp
string frame_id
================================================================================
MSG: builtin_interfaces/Time
int32 sec
uint32 nanosec
================================================================================
MSG: sensor_msgs/PointField
string name
uint32 offset
uint8 datatype
uint32 count
`;

/**
 * Small real indexed MCAP recording for integration tests: duplicate epoch
 * timestamps on a supported lidar channel plus one unsupported channel.
 */
export async function mcapFixture({ compressed = false } = {}) {
    const chunks: Uint8Array[] = [];
    let length = 0;
    const writer = new McapWriter({
        writable: {
            position: () => BigInt(length),
            write: async (bytes) => {
                chunks.push(bytes.slice());
                length += bytes.length;
            }
        },
        compressChunk: compressed
            ? (data) => ({ compression: 'lz4', compressedData: new Uint8Array(compress(data)) })
            : undefined
    });
    await writer.start({ profile: 'ros2', library: 'provider-test' });
    const schemaId = await writer.registerSchema({
        name: 'sensor_msgs/msg/PointCloud2',
        encoding: 'ros2msg',
        data: new TextEncoder().encode(schemaText)
    });
    const channelId = await writer.registerChannel({
        topic: '/lidar',
        schemaId,
        messageEncoding: 'cdr',
        metadata: new Map()
    });
    const encoder = new MessageWriter(parse(schemaText, { ros2: true }));
    const timestamp = 1_789_000_000_000_000_001n;
    for (const x of [1, 4]) {
        const data = new Uint8Array(12);
        const view = new DataView(data.buffer);
        [x, 2, 3].forEach((v, i) => view.setFloat32(i * 4, v, true));
        const payload = encoder.writeMessage({
            header: { stamp: { sec: 1, nanosec: 2 }, frame_id: 'lidar' },
            height: 1,
            width: 1,
            point_step: 12,
            row_step: 12,
            data,
            is_bigendian: false,
            is_dense: true,
            fields: ['x', 'y', 'z'].map((name, i) => ({
                name,
                offset: i * 4,
                datatype: 7,
                count: 1
            }))
        });
        await writer.addMessage({
            channelId,
            logTime: timestamp,
            publishTime: timestamp - 1n,
            sequence: 0,
            data: payload
        });
    }
    const unsupportedChannelId = await writer.registerChannel({
        topic: '/imu',
        schemaId: await writer.registerSchema({
            name: 'sensor_msgs/msg/Imu',
            encoding: 'ros2msg',
            data: new TextEncoder().encode('builtin_interfaces/Time stamp\n')
        }),
        messageEncoding: 'cdr',
        metadata: new Map()
    });
    await writer.addMessage({
        channelId: unsupportedChannelId,
        logTime: timestamp + 1n,
        publishTime: timestamp + 1n,
        sequence: 0,
        data: new Uint8Array(8)
    });
    await writer.end();
    const bytes = new Uint8Array(length);
    let offset = 0;
    for (const chunk of chunks) {
        bytes.set(chunk, offset);
        offset += chunk.length;
    }
    return { bytes, channelId, unsupportedChannelId, timestamp };
}
