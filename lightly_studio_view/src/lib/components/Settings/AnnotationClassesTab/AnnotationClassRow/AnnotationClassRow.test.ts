import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
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

    it('shows the name and a singular or plural annotation count', () => {
        renderRow({ annotationCount: 1 });
        expect(screen.getByText('cat')).toBeInTheDocument();
        expect(screen.getByText(/^\s*1\s+annotation\s*$/)).toBeInTheDocument();
    });

    it('uses the plural for several annotations', () => {
        renderRow({ annotationCount: 2 });
        expect(screen.getByText(/^\s*2\s+annotations\s*$/)).toBeInTheDocument();
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

        await waitFor(() =>
            expect(screen.getByText(/This also deletes 2 annotations/)).toBeInTheDocument()
        );
    });
});
