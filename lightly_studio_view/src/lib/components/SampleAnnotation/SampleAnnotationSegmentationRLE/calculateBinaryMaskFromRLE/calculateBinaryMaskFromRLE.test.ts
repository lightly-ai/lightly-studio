import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import calculateBinaryMaskFromRLE from './calculateBinaryMaskFromRLE';

// Define a minimal interface for only the methods we actually need to mock
interface MinimalMockContext {
    fillStyle: string; // Used by parseColor
    canvas: MockCanvas; // Back-reference needed by implementation accessing ctx.canvas
    fillRect: ReturnType<typeof vi.fn>; // Used by parseColor
    getImageData: ReturnType<typeof vi.fn>; // Used by parseColor
    createImageData: ReturnType<typeof vi.fn>; // Used by main logic
    putImageData: ReturnType<typeof vi.fn>; // Used by main logic
}

// Define a simple mock ImageData structure
interface MockImageData {
    width: number;
    height: number;
    data: Uint8ClampedArray;
}

// Define the structure for the canvas mock object
// Use an interface or type for better clarity
type MockCanvas = {
    width: number;
    height: number;
    getContext: ReturnType<typeof vi.fn>;
    toDataURL: ReturnType<typeof vi.fn>;
};

describe('calculateBinaryMaskFromRLE', () => {
    // Declare mocks at the describe level so they are accessible in tests
    let mockContext: MinimalMockContext;
    let capturedImageData: MockImageData | null = null;
    let documentCreateElementSpy: ReturnType<typeof vi.spyOn>; // To inspect calls

    // Simplified color parsing just for mock getImageData
    const mockGetImageDataForColor = (color: string): MockImageData => {
        const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
        let rgba = { r: 0, g: 0, b: 0, a: 255 }; // Default black
        if (match) {
            rgba = {
                r: parseInt(match[1], 10),
                g: parseInt(match[2], 10),
                b: parseInt(match[3], 10),
                a: match[4] !== undefined ? Math.round(parseFloat(match[4]) * 255) : 255
            };
        } else if (color === 'red') {
            rgba = { r: 255, g: 0, b: 0, a: 255 };
        }
        return {
            width: 1,
            height: 1,
            data: new Uint8ClampedArray([rgba.r, rgba.g, rgba.b, rgba.a])
        };
    };

    beforeEach(() => {
        capturedImageData = null;

        // --- Mock Context ---
        // Create the context mock structure. It will be reused by different canvas mocks.
        mockContext = {
            fillStyle: '#000000',
            canvas: null as unknown as MockCanvas, // Will be linked dynamically by getContext
            fillRect: vi.fn(),
            getImageData: vi.fn((sx, sy, sw, sh) => {
                if (sw === 1 && sh === 1) {
                    return mockGetImageDataForColor(mockContext.fillStyle);
                }
                return { width: sw, height: sh, data: new Uint8ClampedArray(sw * sh * 4) };
            }),
            createImageData: vi.fn((width: number, height: number): MockImageData => {
                return {
                    width,
                    height,
                    data: new Uint8ClampedArray(width * height * 4)
                };
            }),
            putImageData: vi.fn((imageData: MockImageData) => {
                capturedImageData = imageData;
            })
        };

        // --- Mock Canvas Factory ---
        // This function creates a *new* mock canvas object each time
        const createCanvasMock = (): MockCanvas => {
            const canvasInstance: MockCanvas = {
                width: 0,
                height: 0,
                getContext: vi.fn((contextId: string) => {
                    if (contextId === '2d') {
                        // Link the shared context mock back to this specific canvas instance
                        mockContext.canvas = canvasInstance;
                        return mockContext as unknown as CanvasRenderingContext2D;
                    }
                    return null;
                }),
                toDataURL: vi.fn().mockReturnValue('data:image/png;base64,mockDataUrl')
            };
            return canvasInstance;
        };

        // --- Mock document ---
        // Use spyOn to easily track calls and return values
        // Ensure global.document exists or create a basic object
        global.document = global.document || ({ createElement: vi.fn() } as Document);
        documentCreateElementSpy = vi
            .spyOn(global.document, 'createElement')
            .mockImplementation((tagName: string): HTMLElement => {
                if (tagName.toLowerCase() === 'canvas') {
                    // Return a NEW canvas mock each time
                    return createCanvasMock() as unknown as HTMLCanvasElement;
                }
                // Fallback for other elements if necessary, or throw error
                // Use original implementation if available and needed:
                // return documentCreateElementSpy.getMockImplementation()?.(tagName) ?? document.createElement(tagName);
                throw new Error(`document.createElement mock called unexpectedly for: ${tagName}`);
            });
    });

    afterEach(() => {
        // Restore all mocks, including the spyOn
        vi.restoreAllMocks();
    });

    // --- Tests ---

    it('should return minimal data URL for zero dimension', () => {
        const { dataUrl, height } = calculateBinaryMaskFromRLE([1, 1], 0, 'red');
        expect(height).toEqual(0);
        expect(dataUrl).toEqual(
            'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
        );
        // Check that document.createElement was not called for 'canvas'
        expect(documentCreateElementSpy).not.toHaveBeenCalledWith('canvas');
    });

    it('should return minimal data URL for empty segmentation', () => {
        const { dataUrl, height } = calculateBinaryMaskFromRLE([], 100, 'rgba(255, 0, 0, 0.5)');
        expect(height).toEqual(0);
        expect(dataUrl).toEqual(
            'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
        );
        expect(documentCreateElementSpy).not.toHaveBeenCalledWith('canvas');
    });

    it('should generate a binary mask with correct height', () => {
        const segmentation = [5, 10];
        const width = 10;
        const expectedHeight = 2;
        const color = 'rgba(255, 0, 0, 0.5)';

        // Call the function
        const { height, dataUrl } = calculateBinaryMaskFromRLE(segmentation, width, color);

        // Assertions on return values
        expect(height).toEqual(expectedHeight);
        expect(dataUrl).toEqual('data:image/png;base64,mockDataUrl');

        // --- Get the MAIN canvas instance ---
        // The first call to document.createElement('canvas') should be for the main logic
        expect(documentCreateElementSpy).toHaveBeenCalledWith('canvas');
        // Get the result of the *first* call that returned a canvas
        const mainCanvasResult = documentCreateElementSpy.mock.results[0];
        expect(mainCanvasResult.type).toBe('return');
        const mainMockCanvas = mainCanvasResult.value as MockCanvas;

        // Assert on the main canvas properties
        expect(mainMockCanvas.width).toEqual(width); // Check width assignment
        expect(mainMockCanvas.height).toEqual(expectedHeight); // Check height assignment

        // Assert on context method calls
        expect(mockContext.createImageData).toHaveBeenCalledWith(width, expectedHeight);
        expect(mockContext.putImageData).toHaveBeenCalledTimes(1); // Called once for the final image
        expect(mainMockCanvas.toDataURL).toHaveBeenCalledTimes(1); // Called once on the main canvas

        // Check that parseColor's canvas was also created (second call)
        expect(documentCreateElementSpy).toHaveBeenCalledTimes(2);
        const parseColorCanvasResult = documentCreateElementSpy.mock.results[1];
        expect(parseColorCanvasResult.type).toBe('return');
        const parseColorMockCanvas = parseColorCanvasResult.value as MockCanvas;
        // Verify parseColor set its canvas dimensions correctly
        expect(parseColorMockCanvas.width).toEqual(1);
        expect(parseColorMockCanvas.height).toEqual(1);

        // Check context calls related to parseColor
        expect(mockContext.fillRect).toHaveBeenCalledWith(0, 0, 1, 1);
        expect(mockContext.getImageData).toHaveBeenCalledWith(0, 0, 1, 1);
    });

    // Tests for 'should correctly generate binary mask...' and 'should handle fill crossing...'
    // remain the same as they primarily check 'capturedImageData', which is correctly
    // captured by the shared mockContext.putImageData mock.

    it('should correctly generate binary mask from specific RLE pattern', () => {
        // RLE = [1, 2, 1, 4] with width=4 -> [T, F, F, T], [F, F, F, F]
        const segmentation = [1, 2, 1, 4];
        const width = 4;
        const color = 'rgba(255, 0, 0, 0.5)'; // r=255, g=0, b=0, a=128
        const expectedHeight = 2;
        const parsedColor = mockGetImageDataForColor(color).data;
        const r = parsedColor[0],
            g = parsedColor[1],
            b = parsedColor[2],
            a = parsedColor[3];

        const { height } = calculateBinaryMaskFromRLE(segmentation, width, color);

        expect(height).toEqual(expectedHeight);
        expect(mockContext.putImageData).toHaveBeenCalledTimes(1);
        expect(capturedImageData).not.toBeNull();
        if (!capturedImageData) return;

        const data = capturedImageData.data;
        expect(data.length).toBe(width * height * 4); // 32

        // Row 0: [T, F, F, T] (Indices: 0-3, 4-7, 8-11, 12-15)
        expect(data.slice(0, 4)).toEqual(new Uint8ClampedArray([0, 0, 0, 0]));
        expect(data.slice(4, 8)).toEqual(new Uint8ClampedArray([r, g, b, a]));
        expect(data.slice(8, 12)).toEqual(new Uint8ClampedArray([r, g, b, a]));
        expect(data.slice(12, 16)).toEqual(new Uint8ClampedArray([0, 0, 0, 0]));

        // Row 1: [F, F, F, F] (Indices: 16-19, 20-23, 24-27, 28-31)
        expect(data.slice(16, 20)).toEqual(new Uint8ClampedArray([r, g, b, a]));
        expect(data.slice(20, 24)).toEqual(new Uint8ClampedArray([r, g, b, a]));
        expect(data.slice(24, 28)).toEqual(new Uint8ClampedArray([r, g, b, a]));
        expect(data.slice(28, 32)).toEqual(new Uint8ClampedArray([r, g, b, a]));
    });

    it('should handle fill crossing row boundary', () => {
        // RLE = [8, 5] with width=10 -> Row0:[T*8, F, F], Row1:[F, F, F, T*7]
        const segmentation = [8, 5];
        const width = 10;
        const color = 'rgba(0, 0, 255, 1)'; // r=0, g=0, b=255, a=255
        const expectedHeight = 2;
        const parsedColor = mockGetImageDataForColor(color).data;
        const r = parsedColor[0],
            g = parsedColor[1],
            b = parsedColor[2],
            a = parsedColor[3];

        calculateBinaryMaskFromRLE(segmentation, width, color);

        expect(capturedImageData).not.toBeNull();
        if (!capturedImageData) return;
        const data = capturedImageData.data;
        expect(data.length).toBe(width * expectedHeight * 4); // 80

        // Row 0 check (pixels 8, 9 filled - indices 32, 36)
        expect(data.slice(32, 36)).toEqual(new Uint8ClampedArray([r, g, b, a]));
        expect(data.slice(36, 40)).toEqual(new Uint8ClampedArray([r, g, b, a]));
        expect(data.slice(28, 32)).toEqual(new Uint8ClampedArray([0, 0, 0, 0]));

        // Row 1 check (pixels 0, 1, 2 filled - indices 40, 44, 48)
        expect(data.slice(40, 44)).toEqual(new Uint8ClampedArray([r, g, b, a]));
        expect(data.slice(44, 48)).toEqual(new Uint8ClampedArray([r, g, b, a]));
        expect(data.slice(48, 52)).toEqual(new Uint8ClampedArray([r, g, b, a]));
        expect(data.slice(52, 56)).toEqual(new Uint8ClampedArray([0, 0, 0, 0]));
    });
});
