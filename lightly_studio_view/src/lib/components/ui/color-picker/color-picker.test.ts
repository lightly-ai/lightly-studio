import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
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
    beforeAll(() => {
        // jsdom has no pointer capture and no PointerEvent, so pointer coordinates would be lost.
        HTMLElement.prototype.setPointerCapture = vi.fn();
        window.PointerEvent ??= class extends MouseEvent {
            pointerId: number;
            constructor(type: string, init: PointerEventInit = {}) {
                super(type, init);
                this.pointerId = init.pointerId ?? 0;
            }
        } as typeof PointerEvent;
    });

    it('sets the trigger aria-label from triggerLabel', () => {
        render(ColorPicker, { props: { ...defaultProps, triggerLabel: 'Change the color of cat' } });

        expect(screen.getByRole('button', { name: 'Change the color of cat' })).toBeInTheDocument();
    });

    it('previews the selected color while dragging', async () => {
        const onChange = vi.fn();
        render(ColorPicker, { props: { ...defaultProps, onChange } });
        await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));

        const picker = screen.getByRole('slider', { name: 'Saturation and lightness' });
        vi.spyOn(picker, 'getBoundingClientRect').mockReturnValue({
            left: 0,
            top: 0,
            width: 100,
            height: 100
        } as DOMRect);

        await fireEvent.pointerDown(picker, { clientX: 100, clientY: 25, pointerId: 1 });

        await waitFor(() => {
            expect(onChange).toHaveBeenLastCalledWith('#ff8080', 1);
        });
    });

    it('previews a gray preset exactly', async () => {
        const onChange = vi.fn();
        render(ColorPicker, { props: { ...defaultProps, onChange } });
        await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));

        await fireEvent.click(screen.getByTitle('#888888'));

        await waitFor(() => {
            expect(onChange).toHaveBeenLastCalledWith('#888888', 1);
        });
        onChange.mockClear();
        await fireEvent.click(screen.getByRole('button', { name: 'Apply' }));
        expect(onChange).toHaveBeenCalledWith('#888888', 1);
    });

    it('keeps the hue when the saturation box reaches black', async () => {
        const onChange = vi.fn();
        render(ColorPicker, {
            props: { ...defaultProps, initialColor: '#0000ff', onChange }
        });
        await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));
        const box = screen.getByRole('slider', { name: 'Saturation and lightness' });
        vi.spyOn(box, 'getBoundingClientRect').mockReturnValue({
            left: 0,
            top: 0,
            width: 100,
            height: 100
        } as DOMRect);

        await fireEvent.pointerDown(box, { clientX: 100, clientY: 100, pointerId: 1 });
        await waitFor(() => expect(onChange).toHaveBeenLastCalledWith('#000000', 1));
        await fireEvent.pointerUp(box, { pointerId: 1 });
        await fireEvent.pointerDown(box, { clientX: 100, clientY: 50, pointerId: 1 });

        await waitFor(() => expect(onChange).toHaveBeenLastCalledWith('#0000ff', 1));
    });

    it('Reset to default calls onReset and closes without onClose', async () => {
        const onReset = vi.fn();
        const onClose = vi.fn();
        const onChange = vi.fn();
        render(ColorPicker, { props: { ...defaultProps, onReset, onClose, onChange } });
        await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));

        await fireEvent.click(screen.getByRole('button', { name: 'Reset to default' }));

        expect(onReset).toHaveBeenCalledTimes(1);
        expect(onClose).not.toHaveBeenCalled();
        expect(onChange).not.toHaveBeenCalled();
        expect(screen.queryByRole('dialog', { name: 'Color picker' })).not.toBeInTheDocument();
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
        // bits-ui checks that the pointer is outside the panel, so the events need coordinates.
        const outside = { bubbles: true, clientX: 500, clientY: 500 };
        await fireEvent.pointerDown(document.body, outside);
        await fireEvent.pointerUp(document.body, outside);
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

        try {
            render(ColorPicker, { props: defaultProps, target });
            await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));

            expect(parentClick).not.toHaveBeenCalled();
            expect(screen.getByRole('dialog', { name: 'Color picker' })).toBeInTheDocument();
        } finally {
            parent.remove();
        }
    });

    it('works inside a modal dialog without closing it', async () => {
        const onChange = vi.fn();
        render(ColorPickerInDialogTestWrapper, { props: { onChange } });
        await fireEvent.click(screen.getByRole('button', { name: 'Open color picker' }));

        const hexInput = screen.getByRole('textbox');
        hexInput.focus();
        await fireEvent.click(hexInput);
        expect(hexInput).toBe(document.activeElement);

        await fireEvent.click(screen.getByTitle('#0000ff'));
        await waitFor(() => expect(onChange).toHaveBeenLastCalledWith('#0000ff', 1));
        expect(screen.getByRole('dialog', { name: 'Host dialog' })).toBeInTheDocument();
        await fireEvent.keyDown(document.activeElement ?? document.body, { key: 'Escape' });

        expect(screen.queryByRole('dialog', { name: 'Color picker' })).not.toBeInTheDocument();
        expect(screen.getByRole('dialog', { name: 'Host dialog' })).toBeInTheDocument();
    });
});
