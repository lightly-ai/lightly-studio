import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { describe, expect, it, vi } from 'vitest';
import type { SlotRegistry } from '$lib/extensions/slots';
import { registry } from '$lib/extensions/registry';
import ExtensionSlot from './ExtensionSlot.svelte';
import ExtensionSlotTestItem from './ExtensionSlotTestItem.test.svelte';

vi.mock('$lib/extensions/registry', () => ({ registry: {} as SlotRegistry }));

const defaultProps = {
    name: 'dataset.toolbar' as const,
    props: { datasetId: 'dataset-1', collectionId: 'collection-1' },
    children: createRawSnippet(() => ({
        render: () => '<span data-testid="default">Default</span>'
    }))
};

describe('ExtensionSlot', () => {
    it('renders the default content when nothing is registered', () => {
        render(ExtensionSlot, { props: defaultProps });

        expect(screen.getByTestId('default')).toBeInTheDocument();
        expect(screen.queryByTestId('registered')).not.toBeInTheDocument();
    });

    it('renders the registered components with the slot props', () => {
        registry['dataset.toolbar'] = [ExtensionSlotTestItem];
        render(ExtensionSlot, { props: defaultProps });

        expect(screen.getByTestId('registered')).toHaveTextContent('dataset-1/collection-1');
        expect(screen.queryByTestId('default')).not.toBeInTheDocument();
    });
});
