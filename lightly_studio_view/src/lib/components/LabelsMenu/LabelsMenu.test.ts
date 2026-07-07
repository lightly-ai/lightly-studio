import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { writable, type Writable } from 'svelte/store';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import LabelsMenu from './LabelsMenu.svelte';
import type { Annotation } from '$lib/types';

const mocks = vi.hoisted(() => ({
    selectedCollectionIds: null as unknown as Writable<string[]>,
    enforceColoringByClassStore: null as unknown as Writable<boolean>,
    hiddenClassNamesStore: null as unknown as Writable<string[]>,
    toggleClassVisibility: vi.fn()
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

vi.mock('$lib/hooks/useAnnotationClassVisibility/useAnnotationClassVisibility', async () => {
    const { writable } = await import('svelte/store');
    mocks.hiddenClassNamesStore = writable<string[]>([]);
    return {
        useAnnotationClassVisibility: () => ({
            hiddenClassNamesStore: mocks.hiddenClassNamesStore,
            toggleClassVisibility: mocks.toggleClassVisibility,
            isClassHidden: (label: string) => ({
                subscribe: (fn: (v: boolean) => void) => {
                    let hidden: string[] = [];
                    const unsub = mocks.hiddenClassNamesStore.subscribe((v) => {
                        hidden = v;
                        fn(hidden.includes(label));
                    });
                    return unsub;
                }
            })
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
        mocks.hiddenClassNamesStore.set([]);
        mocks.toggleClassVisibility.mockReset();
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

    it('shows visibility toggle buttons when showVisibilityToggle is true', () => {
        render(LabelsMenu, { ...defaultProps, showVisibilityToggle: true });
        expect(screen.getAllByTestId('label-visibility-toggle')).toHaveLength(2);
    });

    it('calls toggleClassVisibility when visibility button is clicked', async () => {
        render(LabelsMenu, { ...defaultProps, showVisibilityToggle: true });
        const [carToggle] = screen.getAllByTestId('label-visibility-toggle');
        await userEvent.click(carToggle);
        expect(mocks.toggleClassVisibility).toHaveBeenCalledWith('car');
    });

    it('shows EyeOff icon for hidden classes', () => {
        mocks.hiddenClassNamesStore.set(['car']);
        render(LabelsMenu, { ...defaultProps, showVisibilityToggle: true });
        expect(screen.getByLabelText('Show annotation class car')).toBeInTheDocument();
        expect(screen.getByLabelText('Hide annotation class person')).toBeInTheDocument();
    });
});
