import type { Meta, StoryObj } from '@storybook/sveltekit';
import ClassSetConfigDialog from './ClassSetConfigDialog.svelte';
import type { ClassSetSelection } from './types';

const baseArgs = {
    open: true,
    sortItems: [
        { value: 'score', label: 'Score' },
        { value: 'name', label: 'Name' }
    ],
    showAllButton: true,
    testIdPrefix: 'class-set-config',
    onApply: () => undefined
};

const classesSelection: ClassSetSelection = {
    mode: 'topN',
    n: 3,
    sortBy: 'score',
    manualClasses: ['dog', 'cat']
};

const metadataSelection: ClassSetSelection = {
    mode: 'topN',
    n: 3,
    sortBy: 'score',
    manualClasses: ['city', 'rural']
};

const meta = {
    title: 'Components/ClassSetConfig/ClassSetConfigDialog',
    component: ClassSetConfigDialog
} satisfies Meta<typeof ClassSetConfigDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Classes: Story = {
    args: {
        ...baseArgs,
        allClasses: ['dog', 'cat', 'bird', 'horse', 'fish', 'rabbit'],
        items: [
            { value: 'dog', label: 'Dog' },
            { value: 'cat', label: 'Cat' },
            { value: 'bird', label: 'Bird' },
            { value: 'horse', label: 'Horse' },
            { value: 'fish', label: 'Fish' },
            { value: 'rabbit', label: 'Rabbit' }
        ],
        selection: classesSelection,
        description: 'Choose how classes are selected for the chart.',
        itemNounPlural: 'classes'
    }
};

export const MetadataValues: Story = {
    args: {
        ...baseArgs,
        allClasses: ['city', 'rural', 'desert', 'mountain', 'coastal'],
        items: [
            { value: 'city', label: 'City' },
            { value: 'rural', label: 'Rural' },
            { value: 'desert', label: 'Desert' },
            { value: 'mountain', label: 'Mountain' },
            { value: 'coastal', label: 'Coastal' }
        ],
        selection: metadataSelection,
        description: 'Choose how categorical values are selected for the chart.',
        itemNounPlural: 'values'
    }
};
