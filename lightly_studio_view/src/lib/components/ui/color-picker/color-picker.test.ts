import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ColorPickerInDialogTestWrapper from './ColorPickerInDialogTestWrapper.test.svelte';
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
        // jsdom has no PointerEvent, and bits-ui checks that the pointer is outside the panel.
        const outside = { bubbles: true, clientX: 500, clientY: 500 };
        await fireEvent(document.body, new MouseEvent('pointerdown', outside));
        await fireEvent(document.body, new MouseEvent('pointerup', outside));
        await fireEvent.click(document.body, outside);

        // bits-ui debounces the outside interaction.
        await waitFor(() => {
            expect(onChange).toHaveBeenLastCalledWith('#ff0000', 1);
        });
        expect(screen.queryByRole('dialog', { name: 'Color picker' })).not.toBeInTheDocument();
    });

    it('restores the original color when pressing Escape after a preview', async () => {
        const onChange = vi.fn();
        render(ColorPicker, { props: { ...defaultProps, onChange } });
        await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));

        await fireEvent.click(screen.getByTitle('#0000ff'));
        await waitFor(() => {
            expect(onChange).toHaveBeenLastCalledWith('#0000ff', 1);
        });
        await fireEvent.keyDown(document.activeElement ?? document.body, { key: 'Escape' });

        expect(onChange).toHaveBeenLastCalledWith('#ff0000', 1);
        expect(screen.queryByRole('dialog', { name: 'Color picker' })).not.toBeInTheDocument();
    });

    it('starts from the new initial color after apply and reopen', async () => {
        const onChange = vi.fn();
        const onClose = vi.fn();
        const { rerender } = render(ColorPicker, {
            props: { ...defaultProps, initialColor: '#ff0000', onChange, onClose }
        });
        await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));
        await fireEvent.click(screen.getByTitle('#0000ff'));
        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
        expect(onClose).toHaveBeenLastCalledWith(true);

        await rerender({ initialColor: '#0000ff' });
        await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));
        expect(screen.getByRole('textbox')).toHaveValue('#0000ff');

        const callCount = onChange.mock.calls.length;
        await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
        expect(onChange).toHaveBeenCalledTimes(callCount);
    });

    it('does not propagate the trigger click to a parent element', async () => {
        const parentClick = vi.fn();
        // Svelte delegates events to the target, so the listener sits on its parent.
        const parent = document.createElement('div');
        const target = parent.appendChild(document.createElement('div'));
        parent.addEventListener('click', parentClick);
        document.body.appendChild(parent);

        render(ColorPicker, { props: defaultProps, target });
        await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));

        expect(parentClick).not.toHaveBeenCalled();
        expect(screen.getByRole('dialog', { name: 'Color picker' })).toBeInTheDocument();
        parent.remove();
    });

    it('works inside a modal dialog without closing it', async () => {
        const onChange = vi.fn();
        render(ColorPickerInDialogTestWrapper, { props: { onChange } });
        await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));

        await fireEvent.click(screen.getByTitle('#0000ff'));
        await waitFor(() => expect(onChange).toHaveBeenLastCalledWith('#0000ff', 1));
        await fireEvent.keyDown(document.activeElement ?? document.body, { key: 'Escape' });

        expect(screen.queryByRole('dialog', { name: 'Color picker' })).not.toBeInTheDocument();
        expect(screen.getByRole('dialog', { name: 'Host dialog' })).toBeInTheDocument();
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
