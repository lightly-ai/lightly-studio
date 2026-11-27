import { describe, expect, it, vi } from 'vitest';
import {
    drawBoxesOnContext,
    drawPolygonsOnContext,
    getRenderTransform,
    getVisibleCanvasRect,
    renderMasks,
    transformBoxes,
    transformPolygons,
    type BoundingBoxInput
} from './maskRendererUtils';
import { rgbaFromBytes } from '$lib/utils/colorConvert';
import { createRenderGeometry as geometry } from './maskRenderer.testFixtures';

const CLIP_RECT = { x: 0, y: 0, width: 200, height: 200 };

const createPolygonContext = () => {
    const ctx = {
        save: vi.fn(),
        restore: vi.fn(),
        beginPath: vi.fn(),
        moveTo: vi.fn(),
        lineTo: vi.fn(),
        closePath: vi.fn(),
        rect: vi.fn(),
        clip: vi.fn(),
        lineWidth: 0,
        strokeStyle: '',
        fillStyle: '',
        fillStyleAtFill: '',
        strokeStyleAtStroke: '',
        fill: vi.fn(() => {
            ctx.fillStyleAtFill = ctx.fillStyle;
        }),
        stroke: vi.fn(() => {
            ctx.strokeStyleAtStroke = ctx.strokeStyle;
        })
    };
    return ctx;
};

describe('maskRendererUtils', () => {
    it('renders a large logical mask into only the output-sized RGBA buffer', () => {
        const pixels = renderMasks(geometry({ sourceWidth: 20_000, sourceHeight: 20_000 }), [
            { rle: [0, 400_000_000], color: [10, 20, 30, 40] }
        ]);

        expect(pixels.byteLength).toBe(200 * 200 * 4);
        expect(pixels.slice(0, 4)).toEqual(new Uint8ClampedArray([10, 20, 30, 40]));
    });

    it('leaves pixels beyond a partial RLE transparent', () => {
        const pixels = renderMasks(
            geometry({ sourceWidth: 4, sourceHeight: 1, outputWidth: 4, outputHeight: 1 }),
            [{ rle: [0, 2], color: [10, 20, 30, 40] }]
        );

        expect(pixels).toEqual(
            new Uint8ClampedArray([10, 20, 30, 40, 10, 20, 30, 40, 0, 0, 0, 0, 0, 0, 0, 0])
        );
    });

    it.each([
        {
            name: 'contain landscape',
            input: geometry({ sourceWidth: 200, sourceHeight: 100 }),
            expected: { scale: 1, offsetX: 0, offsetY: 50 }
        },
        {
            name: 'contain portrait',
            input: geometry({ sourceWidth: 100, sourceHeight: 200 }),
            expected: { scale: 1, offsetX: 50, offsetY: 0 }
        },
        {
            name: 'cover landscape',
            input: geometry({ sourceWidth: 200, sourceHeight: 100, objectFit: 'cover' }),
            expected: { scale: 2, offsetX: -100, offsetY: 0 }
        },
        {
            name: 'cover portrait',
            input: geometry({ sourceWidth: 100, sourceHeight: 200, objectFit: 'cover' }),
            expected: { scale: 2, offsetX: 0, offsetY: -100 }
        },
        {
            name: 'annotation crop',
            input: geometry({
                sourceWidth: 1000,
                sourceHeight: 800,
                outputWidth: 200,
                outputHeight: 100,
                sourceCrop: { x: 100, y: 200, width: 400, height: 200 }
            }),
            expected: { scale: 0.5, offsetX: -50, offsetY: -100 }
        }
    ])('computes the $name transform', ({ input, expected }) => {
        expect(getRenderTransform(input)).toMatchObject(expected);
    });

    it('transforms and clips boxes into output coordinates', () => {
        const boxes: BoundingBoxInput[] = [
            { x: -10, y: 10, width: 30, height: 40, color: [0, 0, 0, 255] }
        ];

        expect(transformBoxes(geometry(), boxes)).toEqual([
            { x: 0, y: 20, width: 40, height: 80, color: [0, 0, 0, 255] }
        ]);
    });

    it('clips boxes to the source crop before applying contain letterboxing', () => {
        const boxes: BoundingBoxInput[] = [
            { x: 0, y: 0, width: 100, height: 100, color: [0, 0, 0, 255] }
        ];

        expect(
            transformBoxes(geometry({ sourceCrop: { x: 25, y: 25, width: 50, height: 25 } }), boxes)
        ).toEqual([{ x: 0, y: 50, width: 200, height: 100, color: [0, 0, 0, 255] }]);
    });

    it('draws transformed boxes with a tile-sized stroke', () => {
        const ctx = {
            save: vi.fn(),
            restore: vi.fn(),
            strokeRect: vi.fn(),
            lineWidth: 0,
            strokeStyle: ''
        } as unknown as OffscreenCanvasRenderingContext2D;
        const boxes: BoundingBoxInput[] = [
            { x: 1, y: 2, width: 3, height: 4, color: [0, 0, 0, 255] }
        ];

        drawBoxesOnContext(ctx, boxes);

        expect(ctx.lineWidth).toBe(2);
        expect(ctx.strokeStyle).toBe('rgba(0, 0, 0, 1)');
        expect(ctx.strokeRect).toHaveBeenCalledWith(1, 2, 3, 4);
    });

    it('maps polygon vertices into output space', () => {
        // contain 200x100 into 200x200: scale 1, offsetY 50
        const [polygon] = transformPolygons(geometry({ sourceWidth: 200, sourceHeight: 100 }), [
            {
                parts: [
                    [
                        [0, 0],
                        [10, 0],
                        [10, 20]
                    ]
                ],
                strokeColor: [1, 2, 3, 255],
                fillColor: [1, 2, 3, 102]
            }
        ]);

        expect(polygon.parts).toEqual([
            [
                [0, 50],
                [10, 50],
                [10, 70]
            ]
        ]);
        expect(polygon.strokeColor).toEqual([1, 2, 3, 255]);
    });

    it('applies the source crop when mapping polygon vertices', () => {
        // crop {x:10,y:10,w:50,h:50} into 200x200: scale 4, offset -40
        const [polygon] = transformPolygons(
            geometry({ sourceCrop: { x: 10, y: 10, width: 50, height: 50 } }),
            [
                {
                    parts: [
                        [
                            [10, 10],
                            [20, 10],
                            [20, 20]
                        ]
                    ],
                    strokeColor: [0, 0, 0, 255],
                    fillColor: [0, 0, 0, 0]
                }
            ]
        );

        expect(polygon.parts).toEqual([
            [
                [0, 0],
                [40, 0],
                [40, 40]
            ]
        ]);
    });

    it('fills all parts of a polygon in one nonzero path, then strokes it', () => {
        const ctx = createPolygonContext();
        const strokeColor: [number, number, number, number] = [255, 0, 0, 255];
        const fillColor: [number, number, number, number] = [255, 0, 0, 102];

        drawPolygonsOnContext(
            ctx,
            [
                {
                    parts: [
                        [
                            [0, 0],
                            [4, 0],
                            [4, 4]
                        ],
                        [
                            [2, 2],
                            [6, 2],
                            [6, 6]
                        ]
                    ],
                    strokeColor,
                    fillColor
                }
            ],
            CLIP_RECT
        );

        expect(ctx.beginPath).toHaveBeenCalledTimes(2);
        expect(ctx.moveTo.mock.calls).toEqual([
            [0, 0],
            [2, 2]
        ]);
        expect(ctx.lineTo.mock.calls).toEqual([
            [4, 0],
            [4, 4],
            [6, 2],
            [6, 6]
        ]);
        expect(ctx.closePath).toHaveBeenCalledTimes(2);
        expect(ctx.fill).toHaveBeenCalledExactlyOnceWith('nonzero');
        expect(ctx.stroke).toHaveBeenCalledTimes(1);
        expect(ctx.lineWidth).toBe(2);
        expect(ctx.fillStyleAtFill).toBe(rgbaFromBytes(fillColor));
        expect(ctx.strokeStyleAtStroke).toBe(rgbaFromBytes(strokeColor));
        expect(ctx.fill.mock.invocationCallOrder[0]).toBeLessThan(
            ctx.stroke.mock.invocationCallOrder[0]
        );
    });

    it('draws parts of opposite winding in the same direction', () => {
        const ctx = createPolygonContext();

        drawPolygonsOnContext(
            ctx,
            [
                {
                    parts: [
                        [
                            [0, 0],
                            [4, 0],
                            [4, 4],
                            [0, 4]
                        ],
                        [
                            [2, 2],
                            [2, 6],
                            [6, 6],
                            [6, 2]
                        ]
                    ],
                    strokeColor: [255, 0, 0, 255],
                    fillColor: [255, 0, 0, 102]
                }
            ],
            CLIP_RECT
        );

        expect(ctx.moveTo.mock.calls).toEqual([
            [0, 0],
            [6, 2]
        ]);
    });

    it('skips parts with fewer than three vertices', () => {
        const ctx = createPolygonContext();

        drawPolygonsOnContext(
            ctx,
            [
                {
                    parts: [
                        [
                            [0, 0],
                            [4, 4]
                        ]
                    ],
                    strokeColor: [255, 0, 0, 255],
                    fillColor: [255, 0, 0, 102]
                }
            ],
            CLIP_RECT
        );

        expect(ctx.moveTo).not.toHaveBeenCalled();
    });

    it('gives the canvas area of a letterboxed image', () => {
        // contain 200x100 into 200x200: scale 1, offsetY 50
        expect(getVisibleCanvasRect(geometry({ sourceWidth: 200, sourceHeight: 100 }))).toEqual({
            x: 0,
            y: 50,
            width: 200,
            height: 100
        });
    });

    it('gives the canvas area of the image inside a source crop that passes the image edge', () => {
        // crop {x:-10,y:0,w:50,h:50} into 200x200: scale 4, offsetX 40
        expect(
            getVisibleCanvasRect(geometry({ sourceCrop: { x: -10, y: 0, width: 50, height: 50 } }))
        ).toEqual({ x: 40, y: 0, width: 160, height: 200 });
    });

    it('clips polygons to the given canvas area before it draws them', () => {
        const ctx = createPolygonContext();

        drawPolygonsOnContext(
            ctx,
            [
                {
                    parts: [
                        [
                            [0, 0],
                            [4, 0],
                            [4, 4]
                        ]
                    ],
                    strokeColor: [255, 0, 0, 255],
                    fillColor: [255, 0, 0, 102]
                }
            ],
            { x: 0, y: 50, width: 200, height: 100 }
        );

        expect(ctx.rect).toHaveBeenCalledExactlyOnceWith(0, 50, 200, 100);
        expect(ctx.clip.mock.invocationCallOrder[0]).toBeLessThan(
            ctx.fill.mock.invocationCallOrder[0]
        );
    });

    it('draws nothing for an empty polygon list', () => {
        const ctx = createPolygonContext();

        drawPolygonsOnContext(ctx, [], CLIP_RECT);

        expect(ctx.save).not.toHaveBeenCalled();
    });
});
