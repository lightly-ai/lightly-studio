import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import AnnotationClassRow from './AnnotationClassRow.svelte';

interface RenderRowOptions {
    annotationCount?: number;
    onRename?: (name: string) => Promise<unknown>;
    onDelete?: () => Promise<unknown>;
}

function renderRow({
    annotationCount = 2,
    onRename = vi.fn().mockResolvedValue(undefined),
    onDelete = vi.fn().mockResolvedValue(undefined)
}: RenderRowOptions = {}) {
    render(AnnotationClassRow, { props: { name: 'cat', annotationCount, onRename, onDelete } });
    return { onRename, onDelete };
}

async function startRename() {
    await fireEvent.click(screen.getByRole('button', { name: 'Rename cat' }));
    return screen.getByRole('textbox', { name: 'New name for cat' });
}

describe('AnnotationClassRow', () => {
    afterEach(() => {
        document.body.innerHTML = '';
    });

    it.each([
        [1, /^\s*1\s+annotation\s*$/],
        [2, /^\s*2\s+annotations\s*$/]
    ])('shows the name and the count for %i annotations', (annotationCount, countText) => {
        renderRow({ annotationCount });
        expect(screen.getByText('cat')).toBeInTheDocument();
        expect(screen.getByText(countText)).toBeInTheDocument();
    });

    it('renames on Enter without submitting the form', async () => {
        const { onRename } = renderRow();
        const input = await startRename();

        await fireEvent.input(input, { target: { value: 'kitty' } });
        const notPrevented = await fireEvent.keyDown(input, { key: 'Enter' });

        expect(notPrevented).toBe(false);
        expect(onRename).toHaveBeenCalledExactlyOnceWith('kitty');
    });

    it('cancels on Escape', async () => {
        const { onRename } = renderRow();
        const input = await startRename();

        await fireEvent.input(input, { target: { value: 'kitty' } });
        await fireEvent.keyDown(input, { key: 'Escape' });

        expect(onRename).not.toHaveBeenCalled();
        expect(screen.getByText('cat')).toBeInTheDocument();
    });

    it.each([
        ['Enter', { isComposing: true }],
        ['Escape', { isComposing: true }],
        // Safari confirms IME text with this Enter.
        ['Enter', { isComposing: false, keyCode: 229 }]
    ])('keeps renaming on %s during IME composition %o', async (key, init) => {
        const { onRename } = renderRow();
        const input = await startRename();

        await fireEvent.input(input, { target: { value: 'kitty' } });
        await fireEvent.keyDown(input, { key, ...init });

        expect(onRename).not.toHaveBeenCalled();
        expect(screen.getByRole('textbox', { name: 'New name for cat' })).toHaveValue('kitty');
    });

    it.each([
        ['unchanged', 'cat'],
        ['blank', '   ']
    ])('does not rename when the name is %s', async (_label, value) => {
        const { onRename } = renderRow();
        const input = await startRename();

        await fireEvent.input(input, { target: { value } });
        await fireEvent.keyDown(input, { key: 'Enter' });

        expect(onRename).not.toHaveBeenCalled();
        expect(screen.getByText('cat')).toBeInTheDocument();
    });

    it('shows the old name when the rename fails', async () => {
        const onRename = vi.fn().mockRejectedValue(new Error('boom'));
        renderRow({ onRename });
        const input = await startRename();

        await fireEvent.input(input, { target: { value: 'kitty' } });
        await fireEvent.keyDown(input, { key: 'Enter' });

        await waitFor(() => expect(onRename).toHaveBeenCalledWith('kitty'));
        expect(screen.getByText('cat')).toBeInTheDocument();
    });

    it('opens the delete dialog', async () => {
        renderRow();
        await fireEvent.click(screen.getByRole('button', { name: 'Delete cat' }));

        const dialog = await screen.findByRole('dialog');
        expect(within(dialog).getByText(/This also deletes/)).toBeInTheDocument();
        expect(within(dialog).getByText('2 annotations')).toBeInTheDocument();
    });
});
