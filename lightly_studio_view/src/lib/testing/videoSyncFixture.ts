import type { FrameView, SampleView } from '$lib/api/lightly_studio_local';
import { encodeBinaryMaskToRLE } from '$lib/components/SampleAnnotation/utils';

export const VIDEO_SYNC_FIXTURE_ROUTE = '/__e2e/video-sync';
export const VIDEO_SYNC_FIXTURE_VIDEO_SRC = '/e2e/synthetic-video-sync.mp4';
export const VIDEO_SYNC_FIXTURE_WIDTH = 160;
export const VIDEO_SYNC_FIXTURE_HEIGHT = 90;
export const VIDEO_SYNC_FIXTURE_FPS = 10;
export const VIDEO_SYNC_FIXTURE_FRAME_COUNT = 20;
export const VIDEO_SYNC_FIXTURE_DURATION_S =
    VIDEO_SYNC_FIXTURE_FRAME_COUNT / VIDEO_SYNC_FIXTURE_FPS;

export const VIDEO_SYNC_FIXTURE_COLORS: Array<[number, number, number]> = [
    [230, 25, 75],
    [60, 180, 75],
    [255, 225, 25],
    [0, 130, 200],
    [245, 130, 48],
    [145, 30, 180],
    [70, 240, 240],
    [240, 50, 230],
    [210, 245, 60],
    [250, 190, 190],
    [0, 128, 128],
    [230, 190, 255],
    [170, 110, 40],
    [255, 250, 200],
    [128, 0, 0],
    [170, 255, 195],
    [128, 128, 0],
    [255, 215, 180],
    [0, 0, 128],
    [128, 128, 128]
];

export const buildVideoSyncFixtureFrameImageURL = (frameIndex: number): string => {
    const [r, g, b] = VIDEO_SYNC_FIXTURE_COLORS[frameIndex] ?? VIDEO_SYNC_FIXTURE_COLORS[0];
    const svg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="${VIDEO_SYNC_FIXTURE_WIDTH}" height="${VIDEO_SYNC_FIXTURE_HEIGHT}" viewBox="0 0 ${VIDEO_SYNC_FIXTURE_WIDTH} ${VIDEO_SYNC_FIXTURE_HEIGHT}">
            <rect width="100%" height="100%" fill="rgb(${r},${g},${b})" />
            <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="monospace" font-size="24" fill="white">${frameIndex}</text>
        </svg>
    `.trim();

    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
};

const createRectMask = ({
    width,
    height,
    x,
    y,
    rectWidth,
    rectHeight
}: {
    width: number;
    height: number;
    x: number;
    y: number;
    rectWidth: number;
    rectHeight: number;
}): Uint8Array => {
    const mask = new Uint8Array(width * height);

    for (let row = y; row < y + rectHeight; row += 1) {
        for (let col = x; col < x + rectWidth; col += 1) {
            mask[row * width + col] = 1;
        }
    }

    return mask;
};

export const buildVideoSyncFixtureFrames = (): FrameView[] => {
    return Array.from({ length: VIDEO_SYNC_FIXTURE_FRAME_COUNT }, (_, index) => {
        const frameNumber = index;
        const x = 24 + index * 4;
        const y = 24;
        const rectWidth = 28;
        const rectHeight = 28;
        const segmentationMask = encodeBinaryMaskToRLE(
            createRectMask({
                width: VIDEO_SYNC_FIXTURE_WIDTH,
                height: VIDEO_SYNC_FIXTURE_HEIGHT,
                x,
                y,
                rectWidth,
                rectHeight
            })
        );

        return {
            frame_number: frameNumber,
            frame_timestamp_s: index / VIDEO_SYNC_FIXTURE_FPS,
            sample_id: `video-sync-frame-${index}`,
            sample: {
                annotations: [
                    {
                        annotation_type: 'instance_segmentation',
                        annotation_label: {
                            annotation_label_name: 'sync-object'
                        },
                        segmentation_details: {
                            x,
                            y,
                            width: rectWidth,
                            height: rectHeight,
                            segmentation_mask: segmentationMask
                        }
                    }
                ]
            } as SampleView
        } as FrameView;
    });
};
