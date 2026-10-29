import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ItemActionMenu from './ItemActionMenu.svelte';

describe('ItemActionMenu', () => {
    it('labels the actions briefly and names the item for screen readers', () => {
        render(ItemActionMenu, {
            props: {
                id: 'source-1',
                name: 'model_v1',
                kind: 'annotation source',
                open: true,
                deletingId: null,
                renamingId: null,
                onOpenChange: vi.fn(),
                onRename: vi.fn(),
                onDelete: vi.fn()
            }
        });

        const rename = screen.getByRole('button', { name: 'Rename annotation source model_v1' });
        const remove = screen.getByRole('button', { name: 'Delete annotation source model_v1' });
        expect(rename).toHaveTextContent(/^Rename$/);
        expect(remove).toHaveTextContent(/^Delete$/);
    });
});
