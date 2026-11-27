import { render, waitFor } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import RotationCursor from './RotationCursor.svelte';

describe('rotation cursor', () => {
    it('shows while dragging the canvas and hides on release or loss of focus', async () => {
        const target = document.createElement('div');
        const canvas = document.createElement('canvas');
        target.append(canvas);
        document.body.append(target);
        const { container, unmount } = render(RotationCursor, {
            props: { target, cursorX: 10, cursorY: 20 }
        });
        const cursor = () => container.querySelector('[aria-hidden="true"]');
        target.dispatchEvent(new MouseEvent('mousedown', { button: 0 }));
        expect(cursor()).toBeNull();
        canvas.dispatchEvent(new MouseEvent('mousedown', { button: 2, bubbles: true }));
        expect(cursor()).toBeNull();
        canvas.dispatchEvent(new MouseEvent('mousedown', { button: 0, bubbles: true }));
        await waitFor(() => expect(cursor()).not.toBeNull());
        window.dispatchEvent(new MouseEvent('mouseup'));
        await waitFor(() => expect(cursor()).toBeNull());
        canvas.dispatchEvent(new MouseEvent('mousedown', { button: 0, bubbles: true }));
        await waitFor(() => expect(cursor()).not.toBeNull());
        window.dispatchEvent(new Event('blur'));
        await waitFor(() => expect(cursor()).toBeNull());
        unmount();
        target.remove();
    });
});
