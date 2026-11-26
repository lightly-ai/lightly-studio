import { describe, expect, it } from 'vitest';
import { getAdjacentCamera, getCameraForDigit, getCameraKeyAction } from './cameraNavigation';

const KEYS = { previous: '[', next: ']' };

function keyEvent(key: string, init: KeyboardEventInit = {}, target?: HTMLElement): KeyboardEvent {
    const event = new KeyboardEvent('keydown', { key, bubbles: true, ...init });
    if (target) Object.defineProperty(event, 'target', { value: target });
    return event;
}

describe('getAdjacentCamera', () => {
    it('wraps around in both directions', () => {
        expect(getAdjacentCamera(['A', 'B', 'C'], 'C', 'next')).toBe('A');
        expect(getAdjacentCamera(['A', 'B', 'C'], 'A', 'previous')).toBe('C');
        expect(getAdjacentCamera(['A', 'B', 'C'], 'B', 'next')).toBe('C');
    });

    it('returns undefined for a single camera', () => {
        expect(getAdjacentCamera(['A'], 'A', 'next')).toBeUndefined();
    });

    it('returns undefined when the current camera is missing', () => {
        expect(getAdjacentCamera(['A', 'B'], 'X', 'next')).toBeUndefined();
    });
});

describe('getCameraKeyAction', () => {
    it('maps the configured keys and Shift+Arrow keys', () => {
        expect(getCameraKeyAction(keyEvent('['), KEYS)).toBe('previous');
        expect(getCameraKeyAction(keyEvent(']'), KEYS)).toBe('next');
        expect(getCameraKeyAction(keyEvent('Q'), { previous: 'q', next: 'w' })).toBe('previous');
        expect(getCameraKeyAction(keyEvent('ArrowRight', { shiftKey: true }), KEYS)).toBe('next');
        expect(getCameraKeyAction(keyEvent('ArrowLeft', { shiftKey: true }), KEYS)).toBe(
            'previous'
        );
    });

    it('ignores plain arrows and modified keys', () => {
        expect(getCameraKeyAction(keyEvent('ArrowRight'), KEYS)).toBeUndefined();
        expect(getCameraKeyAction(keyEvent(']', { ctrlKey: true }), KEYS)).toBeUndefined();
    });

    it('ignores keys from text inputs', () => {
        const input = document.createElement('input');
        expect(getCameraKeyAction(keyEvent(']', {}, input), KEYS)).toBeUndefined();
    });
});

describe('getCameraForDigit', () => {
    it('maps digits to camera names', () => {
        expect(getCameraForDigit(keyEvent('2'), ['A', 'B'])).toBe('B');
    });

    it('returns undefined for out-of-range digits, zero and modified keys', () => {
        expect(getCameraForDigit(keyEvent('3'), ['A', 'B'])).toBeUndefined();
        expect(getCameraForDigit(keyEvent('0'), ['A', 'B'])).toBeUndefined();
        expect(getCameraForDigit(keyEvent('1', { shiftKey: true }), ['A'])).toBeUndefined();
    });

    it('ignores keys from text inputs', () => {
        const input = document.createElement('input');
        expect(getCameraForDigit(keyEvent('1', {}, input), ['A'])).toBeUndefined();
    });
});
