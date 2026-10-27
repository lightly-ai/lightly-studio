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

    it('opens inside a transformed modal dialog and positions relative to it', async () => {
        const modal = document.createElement('div');
        modal.setAttribute('role', 'dialog');
        modal.style.transform = 'translate(-50%, -50%)';
        document.body.appendChild(modal);
        vi.spyOn(modal, 'getBoundingClientRect').mockReturnValue({
            left: 100,
            top: 50
        } as DOMRect);

        render(ColorPicker, { props: defaultProps, target: modal });
        await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));

        const panel = screen.getByRole('dialog', { name: 'Color picker' });
        expect(modal).toContainElement(panel);
        // The trigger is at (0, 0), so the viewport position is clamped to (10, 10).
        await waitFor(() => {
            expect(panel.style.left).toBe('-90px');
            expect(panel.style.top).toBe('-40px');
        });

        modal.remove();
    });

    it('positions relative to the viewport outside a modal dialog', async () => {
        // jsdom computes an empty transform instead of the browser default 'none'.
        document.documentElement.style.transform = 'none';
        document.body.style.transform = 'none';
        render(ColorPicker, { props: defaultProps });
        await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));

        const panel = screen.getByRole('dialog', { name: 'Color picker' });
        expect(panel.parentElement).toBe(document.body);
        await waitFor(() => {
            expect(panel.style.left).toBe('10px');
            expect(panel.style.top).toBe('10px');
        });

        document.documentElement.style.transform = '';
        document.body.style.transform = '';
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
