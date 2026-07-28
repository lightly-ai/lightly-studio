<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import ParameterTable from './ParameterTable.svelte';

    const COLUMNS = ['prompt', 'label'];

    const { Story } = defineMeta({
        title: 'Components/Operator/ParameterTable',
        component: ParameterTable,
        tags: ['autodocs'],
        parameters: {
            layout: 'centered'
        },
        argTypes: {
            name: {
                description: 'Parameter name. Used as the label and as the `data-testid` prefix.',
                control: 'text'
            },
            value: {
                description: 'Current rows. Each row maps every column name to a string cell.',
                control: 'object'
            },
            columns: {
                description: 'Column names in display order, taken from the parameter definition.',
                control: 'object'
            },
            required: {
                description: 'Whether the operator requires a value before it can be executed.',
                control: 'boolean'
            },
            isMissing: {
                description: 'Whether the current value fails the required check.',
                control: 'boolean'
            },
            description: {
                description: 'Helper text shown below the label.',
                control: 'text'
            },
            onUpdate: {
                description: 'Called with the full new row array on every add, edit and remove.',
                control: false
            }
        }
    });
</script>

<Story
    name="Empty"
    args={{
        name: 'prompts',
        value: [],
        columns: COLUMNS,
        required: true,
        isMissing: false,
        description: 'Prompt to segment with and the label to assign to the masks.',
        onUpdate: fn()
    }}
/>

<Story
    name="WithRows"
    args={{
        name: 'prompts',
        value: [
            { prompt: 'person', label: 'pedestrian' },
            { prompt: 'car', label: 'vehicle' }
        ],
        columns: COLUMNS,
        required: true,
        isMissing: false,
        description: 'Prompt to segment with and the label to assign to the masks.',
        onUpdate: fn()
    }}
/>

<Story
    name="IncompleteRow"
    args={{
        name: 'prompts',
        value: [{ prompt: 'person', label: '' }],
        columns: COLUMNS,
        required: true,
        isMissing: true,
        description: 'Prompt to segment with and the label to assign to the masks.',
        onUpdate: fn()
    }}
/>

<Story
    name="ManyRows"
    args={{
        name: 'prompts',
        value: [
            { prompt: 'person', label: 'pedestrian' },
            { prompt: 'car', label: 'vehicle' },
            { prompt: 'dog', label: 'animal' },
            { prompt: 'tree', label: 'plant' },
            { prompt: 'bicycle', label: 'vehicle' },
            { prompt: 'traffic light', label: 'signal' },
            { prompt: 'building', label: 'structure' }
        ],
        columns: COLUMNS,
        required: true,
        isMissing: false,
        description: 'Prompt to segment with and the label to assign to the masks.',
        onUpdate: fn()
    }}
/>

<Story
    name="SingleColumn"
    args={{
        name: 'classes',
        value: [{ class: 'person' }, { class: 'car' }],
        columns: ['class'],
        required: false,
        isMissing: false,
        onUpdate: fn()
    }}
/>
