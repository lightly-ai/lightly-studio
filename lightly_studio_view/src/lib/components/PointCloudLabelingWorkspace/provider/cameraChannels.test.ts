import { describe, expect, it } from 'vitest';
import { cameraEncoding } from './cameraChannels';

const ros2msg = (name: string) => ({ name, encoding: 'ros2msg' });

describe('cameraEncoding', () => {
    it('recognizes each camera schema, under either naming convention', () => {
        expect(cameraEncoding('cdr', ros2msg('foxglove_msgs/msg/CompressedVideo'))).toBe(
            'compressed-video'
        );
        expect(cameraEncoding('cdr', ros2msg('sensor_msgs/msg/CompressedImage'))).toBe(
            'compressed-image'
        );
        expect(cameraEncoding('cdr', ros2msg('sensor_msgs/CompressedImage'))).toBe(
            'compressed-image'
        );
        expect(cameraEncoding('cdr', ros2msg('sensor_msgs/msg/Image'))).toBe('raw-image');
    });

    it('ignores channels that are not camera imagery', () => {
        expect(cameraEncoding('cdr', ros2msg('sensor_msgs/msg/PointCloud2'))).toBeNull();
        expect(cameraEncoding('cdr', ros2msg('tf2_msgs/msg/TFMessage'))).toBeNull();
        expect(cameraEncoding('cdr', undefined)).toBeNull();
    });

    it('ignores imagery this decoder cannot read', () => {
        expect(cameraEncoding('protobuf', ros2msg('foxglove.CompressedImage'))).toBeNull();
        expect(
            cameraEncoding('cdr', { name: 'foxglove.CompressedImage', encoding: 'protobuf' })
        ).toBeNull();
    });
});
