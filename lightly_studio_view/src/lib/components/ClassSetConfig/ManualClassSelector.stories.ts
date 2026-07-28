import type { Meta, StoryObj } from '@storybook/sveltekit';
import ManualClassSelector from './ManualClassSelector.svelte';

const meta = {
    title: 'Components/ClassSetConfig/ManualClassSelector',
    component: ManualClassSelector,
    args: {
        selected: ['dog', 'cat'],
        allClasses: ['dog', 'cat', 'bird', 'horse', 'fish'],
        itemNoun: 'animal',
        itemNounPlural: 'animals',
        searchTestId: 'manual-class-selector-search'
    }
} satisfies Meta<typeof ManualClassSelector>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
