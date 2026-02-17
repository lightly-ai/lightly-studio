import { createEvent, fireEvent, render, screen, within } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import CreateCaptionField from './CreateCaptionField.svelte';
import CreateCaptionFieldTestWrapper from './CreateCaptionFieldTestWrapper.svelte';

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

    it('prevents opening another draft while one draft is active', async () => {
        const { container } = render(CreateCaptionFieldTestWrapper);

        const addButtons = container.querySelectorAll('[data-testid="add-caption-button"]');
        expect(addButtons).toHaveLength(2);

        await fireEvent.click(addButtons[0]);
        expect(screen.getAllByTestId('new-caption-input')).toHaveLength(1);

        const secondAddButton = container.querySelectorAll('[data-testid="add-caption-button"]')[0];
        expect(secondAddButton).toBeDisabled();
        await fireEvent.click(secondAddButton);

        expect(screen.getAllByTestId('new-caption-input')).toHaveLength(1);
        expect(
            within(screen.getByTestId('row-a')).getByTestId('new-caption-input')
        ).toBeInTheDocument();
    });
});
