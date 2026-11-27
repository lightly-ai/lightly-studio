interface Size {
    width: number;
    height: number;
}

// Reads the RGBA pixels of a bitmap drawn at the given size, on one reused canvas.
export const createPixelReader = (size: Size) => {
    const context = new OffscreenCanvas(size.width, size.height).getContext('2d', {
        willReadFrequently: true
    })!;
    // Replaces the pixels on each draw, so transparent areas never show the previous image.
    context.globalCompositeOperation = 'copy';
    return (image: ImageBitmap): Uint8ClampedArray => {
        context.drawImage(image, 0, 0, size.width, size.height);
        return context.getImageData(0, 0, size.width, size.height).data;
    };
};
