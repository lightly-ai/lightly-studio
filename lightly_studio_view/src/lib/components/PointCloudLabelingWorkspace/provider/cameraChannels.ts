/** How a camera channel carries its pictures, which decides how a frame is decoded. */
export type CameraEncoding = 'compressed-video' | 'compressed-image' | 'raw-image';

/**
 * The encoding a camera channel uses, or null when the channel is not camera imagery.
 *
 * Matched on the schema's suffix rather than its full name: the same message travels as
 * `sensor_msgs/msg/CompressedImage` and `sensor_msgs/CompressedImage` depending on the
 * generator, and `foxglove_msgs/msg/CompressedVideo` alongside both.
 */
export function cameraEncoding(
    messageEncoding: string,
    schema: { name: string; encoding: string } | undefined
): CameraEncoding | null {
    if (messageEncoding !== 'cdr' || schema?.encoding !== 'ros2msg') return null;
    if (schema.name.endsWith('CompressedVideo')) return 'compressed-video';
    if (schema.name.endsWith('CompressedImage')) return 'compressed-image';
    if (schema.name.endsWith('/Image')) return 'raw-image';
    return null;
}
