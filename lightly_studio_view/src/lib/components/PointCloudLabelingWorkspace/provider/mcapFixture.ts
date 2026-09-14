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

const transformSchemaText = `geometry_msgs/TransformStamped[] transforms
================================================================================
MSG: geometry_msgs/TransformStamped
std_msgs/Header header
string child_frame_id
geometry_msgs/Transform transform
================================================================================
MSG: std_msgs/Header
builtin_interfaces/Time stamp
string frame_id
================================================================================
MSG: builtin_interfaces/Time
int32 sec
uint32 nanosec
================================================================================
MSG: geometry_msgs/Transform
geometry_msgs/Vector3 translation
geometry_msgs/Quaternion rotation
================================================================================
MSG: geometry_msgs/Vector3
float64 x
float64 y
float64 z
================================================================================
MSG: geometry_msgs/Quaternion
float64 x
float64 y
float64 z
float64 w
`;

/** Where the fixture's second lidar sits on its vehicle, in the CABIN frame. */
export const RIGHT_LIDAR_MOUNT = { x: 10, y: -5, z: 1 };

/**
 * Small real indexed MCAP recording for integration tests: duplicate epoch
 * timestamps on a supported lidar channel plus one unsupported channel.
 *
 * `fused` adds what a vehicle recording really looks like: a second lidar, in its own
 * frame, and the `/tf_static` that says where both sit on the vehicle. `omitTransforms`
 * then leaves that `/tf_static` out, which is a recording whose sensors cannot be aligned.
 */
export async function mcapFixture({
    compressed = false,
    fused = false,
    omitTransforms = false
} = {}) {
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
        await writeSweep(writer, encoder, {
            channelId,
            timestamp,
            frameId: 'lidar',
            point: [x, 2, 3]
        });
    }

    let rightChannelId: number | undefined;
    if (fused) {
        rightChannelId = await writer.registerChannel({
            topic: '/lidar_right',
            schemaId,
            messageEncoding: 'cdr',
            metadata: new Map()
        });
        // One point at the sensor's own origin, so a fused frame shows it exactly at the
        // mount `/tf_static` gives that sensor.
        await writeSweep(writer, encoder, {
            channelId: rightChannelId,
            timestamp,
            frameId: 'lidar_right',
            point: [0, 0, 0]
        });
        if (!omitTransforms) await writeStaticTransforms(writer, timestamp);
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
    return { bytes, channelId, rightChannelId, unsupportedChannelId, timestamp };
}

interface SweepOptions {
    channelId: number;
    timestamp: bigint;
    frameId: string;
    point: [number, number, number];
}

async function writeSweep(
    writer: McapWriter,
    encoder: MessageWriter,
    { channelId, timestamp, frameId, point }: SweepOptions
) {
    const data = new Uint8Array(12);
    const view = new DataView(data.buffer);
    point.forEach((value, index) => view.setFloat32(index * 4, value, true));
    await writer.addMessage({
        channelId,
        logTime: timestamp,
        publishTime: timestamp - 1n,
        sequence: 0,
        data: encoder.writeMessage({
            header: { stamp: { sec: 1, nanosec: 2 }, frame_id: frameId },
            height: 1,
            width: 1,
            point_step: 12,
            row_step: 12,
            data,
            is_bigendian: false,
            is_dense: true,
            fields: ['x', 'y', 'z'].map((name, index) => ({
                name,
                offset: index * 4,
                datatype: 7,
                count: 1
            }))
        })
    });
}

/** Publishes both lidars as children of the vehicle frame, the way a rig is calibrated. */
async function writeStaticTransforms(writer: McapWriter, timestamp: bigint) {
    const channelId = await writer.registerChannel({
        topic: '/tf_static',
        schemaId: await writer.registerSchema({
            name: 'tf2_msgs/msg/TFMessage',
            encoding: 'ros2msg',
            data: new TextEncoder().encode(transformSchemaText)
        }),
        messageEncoding: 'cdr',
        metadata: new Map()
    });
    const identity = { x: 0, y: 0, z: 0, w: 1 };
    await writer.addMessage({
        channelId,
        logTime: timestamp - 1n,
        publishTime: timestamp - 1n,
        sequence: 0,
        data: new MessageWriter(parse(transformSchemaText, { ros2: true })).writeMessage({
            transforms: [
                {
                    header: { stamp: { sec: 1, nanosec: 0 }, frame_id: 'CABIN' },
                    child_frame_id: 'lidar',
                    transform: { translation: { x: 0, y: 0, z: 0 }, rotation: identity }
                },
                {
                    header: { stamp: { sec: 1, nanosec: 0 }, frame_id: 'CABIN' },
                    child_frame_id: 'lidar_right',
                    transform: { translation: RIGHT_LIDAR_MOUNT, rotation: identity }
                }
            ]
        })
    });
}
