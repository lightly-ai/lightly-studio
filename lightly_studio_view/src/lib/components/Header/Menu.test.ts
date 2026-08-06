import { render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import type { CollectionView } from '$lib/api/lightly_studio_local';
import Menu from './Menu.svelte';

vi.mock('$lib/components/Select', async () => ({
    Select: (await import('./MenuTestSelect.svelte')).default
}));
vi.mock('$lib/hooks', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/hooks')>()),
    useGlobalStorage: () => ({ filteredSampleCount: writable(0) })
}));
vi.mock('$lib/hooks/useClassifiers/useClassifiersMenu', () => ({
    useClassifiersMenu: () => ({ openClassifiersMenu: vi.fn() })
}));
vi.mock('$lib/hooks/useSamplingDialog/useSamplingDialog', () => ({
    useSamplingDialog: () => ({ openSamplingDialog: vi.fn() })
}));
vi.mock('$lib/hooks/useExportDialog/useExportDialog', () => ({
    useExportDialog: () => ({ openExportDialog: vi.fn() })
}));
vi.mock('$lib/hooks/useSettingsDialog/useSettingsDialog', () => ({
    useSettingsDialog: () => ({ openSettingsDialog: vi.fn() })
}));
vi.mock('$lib/hooks/useOperatorsDialog/useOperatorsDialog', () => ({
    useOperatorsDialog: () => ({ openOperatorsDialog: vi.fn() })
}));
vi.mock('$lib/hooks/useClassesDialog/useClassesDialog', () => ({
    useClassesDialog: () => ({ openClassesDialog: vi.fn() })
}));

const collection = {
    collection_id: 'collection-id',
    name: 'Collection',
    sample_type: 'image',
    created_at: new Date(),
    updated_at: new Date()
} as CollectionView;

describe('Menu', () => {
    it('shows Classes for viewers', () => {
        render(Menu, {
            props: {
                collection,
                user: { username: 'viewer', email: 'viewer@test.com', role: 'viewer' }
            }
        });

        expect(screen.getByTestId('menu-classes')).toHaveTextContent('Classes');
    });
});
