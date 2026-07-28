import type { Meta, StoryObj } from '@storybook/sveltekit';
import ManualClassSelector from './ManualClassSelector.svelte';

const meta = {
    title: 'Components/ClassSetConfig/ManualClassSelector',
    component: ManualClassSelector
} satisfies Meta<typeof ManualClassSelector>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Classes: Story = {
    args: {
        selected: ['dog', 'cat'],
        allClasses: ['dog', 'cat', 'bird', 'horse', 'fish'],
        itemNoun: 'animal',
        itemNounPlural: 'animals',
        searchTestId: 'manual-class-selector-search'
    }
};

export const MetadataValuesWithItems: Story = {
    args: {
        selected: ['city', 'rural'],
        allClasses: ['city', 'rural', 'desert', 'mountain', 'coastal'],
        items: [
            { value: 'city', label: 'City' },
            { value: 'rural', label: 'Rural' },
            { value: 'desert', label: 'Desert' },
            { value: 'mountain', label: 'Mountain' },
            { value: 'coastal', label: 'Coastal' }
        ],
        itemNoun: 'value',
        itemNounPlural: 'values',
        searchTestId: 'manual-metadata-selector-search'
    }
};
