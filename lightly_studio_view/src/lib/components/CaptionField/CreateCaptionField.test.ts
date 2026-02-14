import { createEvent, fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import CreateCaptionField from './CreateCaptionField.svelte';

describe('CreateCaptionField', () => {
    it('stops space key propagation to prevent parent navigation handlers', async () => {
        render(CreateCaptionField, {
            props: {
                onCreate: vi.fn()
            }
        });

        await fireEvent.click(screen.getByTestId('add-caption-button'));

        const input = screen.getByTestId('new-caption-input');
        const event = createEvent.keyDown(input, { key: ' ', code: 'Space' });
        const stopPropagation = vi.fn();
        const stopImmediatePropagation = vi.fn();
        const preventDefault = vi.fn();
        event.stopPropagation = stopPropagation;
        event.stopImmediatePropagation = stopImmediatePropagation;
        event.preventDefault = preventDefault;

        await fireEvent(input, event);

        expect(stopPropagation).toHaveBeenCalledOnce();
        expect(stopImmediatePropagation).toHaveBeenCalledOnce();
        expect(preventDefault).not.toHaveBeenCalled();
    });
});
