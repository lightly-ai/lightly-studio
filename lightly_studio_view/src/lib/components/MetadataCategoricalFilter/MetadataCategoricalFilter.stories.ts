import type { Meta, StoryObj } from '@storybook/sveltekit';
import MetadataCategoricalFilter from './MetadataCategoricalFilter.svelte';
import type { CategoricalMetadataBucket } from '$lib/hooks/useCategoricalMetadataDistribution/types';
import { fn } from 'storybook/test';

const buckets: CategoricalMetadataBucket[] = [
    { id: 'city-1', kind: 'value', value: 'Berlin', label: 'Berlin', count: 42 },
    { id: 'city-2', kind: 'value', value: 'Paris', label: 'Paris', count: 31 },
    { id: 'city-3', kind: 'value', value: 'Tokyo', label: 'Tokyo', count: 18 }
];

const meta = {
    title: 'Components/DatasetDistributionPanel/MetadataCategoricalFilter',
    component: MetadataCategoricalFilter,
    args: {
        buckets,
        selectedValues: ['Berlin'],
        loading: false,
        onToggle: fn(),
        onClear: fn()
    }
} satisfies Meta<typeof MetadataCategoricalFilter>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
