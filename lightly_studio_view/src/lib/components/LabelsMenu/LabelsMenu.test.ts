import { render, screen } from '@testing-library/svelte';
import { writable, type Writable } from 'svelte/store';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import LabelsMenu from './LabelsMenu.svelte';
import type { Annotation } from '$lib/types';

const mocks = vi.hoisted(() => ({
    selectedCollectionIds: null as unknown as Writable<string[]>,
    enforceColoringByClassStore: null as unknown as Writable<boolean>
}));

vi.mock('$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter', async () => {
    const { writable } = await import('svelte/store');
    mocks.selectedCollectionIds = writable<string[]>([]);
    return {
        useAnnotationCollectionsFilter: () => ({
            selectedCollectionIds: mocks.selectedCollectionIds
        })
    };
});

vi.mock('$lib/hooks/useSettings', async () => {
    const { writable } = await import('svelte/store');
    mocks.enforceColoringByClassStore = writable<boolean>(false);
    return {
        useSettings: () => ({
            enforceColoringByClassStore: mocks.enforceColoringByClassStore
        })
    };
});

vi.mock('$lib/hooks/useCustomLabelColors', async () => {
    const { writable } = await import('svelte/store');
    return {
        useCustomLabelColors: () => ({
            customLabelColorsStore: writable({}),
            colorVersion: writable(0),
            getCustomColor: () => undefined,
            setCustomColor: vi.fn(),
            hasCustomColor: () => false,
            deleteCustomColor: vi.fn(),
            clearCustomColors: vi.fn()
        })
    };
});

describe('LabelsMenu', () => {
    const twoLabels = writable<Annotation[]>([
        { label_name: 'car', current_count: 1, total_count: 1, selected: true },
        { label_name: 'person', current_count: 1, total_count: 1, selected: true }
    ]);
    const defaultProps = {
        annotationFilterRows: twoLabels,
        onToggleAnnotationFilter: vi.fn()
    };

    beforeEach(() => {
        mocks.selectedCollectionIds.set([]);
        mocks.enforceColoringByClassStore.set(false);
    });

    it('shows class color legends when only one source is selected', () => {
        mocks.selectedCollectionIds.set(['col-a']);
        render(LabelsMenu, defaultProps);
        expect(screen.getAllByTestId('label-color-legend')).toHaveLength(2);
    });

    it('hides class color legends when multiple sources are selected and enforce is disabled', () => {
        mocks.selectedCollectionIds.set(['col-a', 'col-b']);
        mocks.enforceColoringByClassStore.set(false);
        render(LabelsMenu, defaultProps);
        expect(screen.queryByTestId('label-color-legend')).not.toBeInTheDocument();
    });

    it('shows class color legends when multiple sources are selected and enforce is enabled', () => {
        mocks.selectedCollectionIds.set(['col-a', 'col-b']);
        mocks.enforceColoringByClassStore.set(true);
        render(LabelsMenu, defaultProps);
        expect(screen.getAllByTestId('label-color-legend')).toHaveLength(2);
    });

    it('renders a row for each annotation label', () => {
        render(LabelsMenu, defaultProps);
        expect(screen.getAllByTestId('labels-menu-item')).toHaveLength(2);
        expect(screen.getByText('car')).toBeInTheDocument();
        expect(screen.getByText('person')).toBeInTheDocument();
    });
});
