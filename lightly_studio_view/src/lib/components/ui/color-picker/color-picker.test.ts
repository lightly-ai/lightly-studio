import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ColorPicker from './color-picker.svelte';

const children = createRawSnippet(() => ({
    render: () => '<span>Open color picker</span>'
}));

const defaultProps = { children };

afterEach(() => {
    vi.restoreAllMocks();
});

describe('ColorPicker', () => {
    it('previews the selected color while dragging', async () => {
        const onChange = vi.fn();
        render(ColorPicker, { props: { ...defaultProps, onChange } });
        await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));

        const picker = screen.getByRole('dialog', {
            name: 'Saturation and lightness picker'
        });
        vi.spyOn(picker, 'getBoundingClientRect').mockReturnValue({
            left: 0,
            top: 0,
            width: 100,
            height: 100
        } as DOMRect);

        await fireEvent.mouseDown(picker, { clientX: 100, clientY: 25 });

        await waitFor(() => {
            expect(onChange).toHaveBeenLastCalledWith('#ff8080', 1);
        });
        await fireEvent.mouseUp(document);
    });

    it('restores the original color when cancelling a preview', async () => {
        const onChange = vi.fn();
        render(ColorPicker, { props: { ...defaultProps, onChange } });
        await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));

        await fireEvent.click(screen.getByTitle('#0000ff'));
        await waitFor(() => {
            expect(onChange).toHaveBeenLastCalledWith('#0000ff', 1);
        });
        await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

        expect(onChange).toHaveBeenLastCalledWith('#ff0000', 1);
    });

    it('restores the original color when dismissing a preview', async () => {
        const onChange = vi.fn();
        render(ColorPicker, { props: { ...defaultProps, onChange } });
        await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));

        await fireEvent.click(screen.getByTitle('#0000ff'));
        await waitFor(() => {
            expect(onChange).toHaveBeenLastCalledWith('#0000ff', 1);
        });
        await fireEvent.mouseDown(document.body);

        expect(onChange).toHaveBeenLastCalledWith('#ff0000', 1);
        expect(screen.queryByRole('dialog', { name: 'Color picker' })).not.toBeInTheDocument();
    });

    it.each(['Saturation and lightness picker', 'Hue picker'])(
        'registers one mousemove listener for a drag on %s',
        async (pickerName) => {
            render(ColorPicker, { props: defaultProps });
            await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));

            const addEventListenerSpy = vi.spyOn(document, 'addEventListener');
            const picker = screen.getByRole('dialog', { name: pickerName });
            vi.spyOn(picker, 'getBoundingClientRect').mockReturnValue({
                left: 0,
                top: 0,
                width: 100,
                height: 100
            } as DOMRect);

            await fireEvent.mouseDown(picker, { clientX: 25, clientY: 25 });
            await fireEvent.mouseMove(document, { clientX: 50, clientY: 50 });
            await fireEvent.mouseMove(document, { clientX: 75, clientY: 75 });

            const mouseMoveRegistrations = addEventListenerSpy.mock.calls.filter(
                ([eventName]) => eventName === 'mousemove'
            );
            expect(mouseMoveRegistrations).toHaveLength(1);

            await fireEvent.mouseUp(document);
        }
    );
});
