import { describe, expect, it } from 'vitest';
import {
    brushSizeToSliderPosition,
    clampBrushSize,
    getWheelStep,
    parseBrushSize,
    sliderPositionToBrushSize
} from './brushSize';

describe('clampBrushSize', () => {
    it('keeps the size within 1 to 500 px', () => {
        expect(clampBrushSize(0)).toBe(1);
        expect(clampBrushSize(501)).toBe(500);
        expect(clampBrushSize(37)).toBe(37);
    });

    it('rounds to a whole number', () => {
        expect(clampBrushSize(12.6)).toBe(13);
    });
});

describe('sliderPositionToBrushSize', () => {
    it('maps the slider ends to 1 and 500 px', () => {
        expect(sliderPositionToBrushSize(0)).toBe(1);
        expect(sliderPositionToBrushSize(1000)).toBe(500);
    });

    it('gives small sizes most of the travel', () => {
        expect(sliderPositionToBrushSize(500)).toBe(22);
    });

    it('grows with the position', () => {
        expect(sliderPositionToBrushSize(100)).toBe(2);
        expect(sliderPositionToBrushSize(250)).toBe(5);
        expect(sliderPositionToBrushSize(750)).toBe(106);
    });
});

describe('brushSizeToSliderPosition', () => {
    it('maps 1 and 500 px to the slider ends', () => {
        expect(brushSizeToSliderPosition(1)).toBe(0);
        expect(brushSizeToSliderPosition(500)).toBe(1000);
    });

    it('round-trips small sizes exactly', () => {
        expect(sliderPositionToBrushSize(brushSizeToSliderPosition(2))).toBe(2);
        expect(sliderPositionToBrushSize(brushSizeToSliderPosition(10))).toBe(10);
        expect(sliderPositionToBrushSize(brushSizeToSliderPosition(37))).toBe(37);
    });
});

describe('getWheelStep', () => {
    it('steps by about 10% of the size, at least 1 px', () => {
        expect(getWheelStep(1)).toBe(1);
        expect(getWheelStep(14)).toBe(1);
        expect(getWheelStep(15)).toBe(2);
        expect(getWheelStep(100)).toBe(10);
        expect(getWheelStep(500)).toBe(50);
    });
});

describe('parseBrushSize', () => {
    it('reads whole numbers and clamps them', () => {
        expect(parseBrushSize('37')).toBe(37);
        expect(parseBrushSize(' 12 ')).toBe(12);
        expect(parseBrushSize('0')).toBe(1);
        expect(parseBrushSize('900')).toBe(500);
    });

    it('rejects empty and invalid text', () => {
        expect(parseBrushSize('')).toBeUndefined();
        expect(parseBrushSize('abc')).toBeUndefined();
        expect(parseBrushSize('12.5')).toBeUndefined();
        expect(parseBrushSize('-3')).toBeUndefined();
    });
});
