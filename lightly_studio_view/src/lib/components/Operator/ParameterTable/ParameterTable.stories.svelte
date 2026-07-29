<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import ParameterTable from './ParameterTable.svelte';

    // Shared across all stories: every change is logged in the Actions panel.
    const { Story } = defineMeta({
        title: 'Components/Operator/ParameterTable',
        component: ParameterTable,
        tags: ['autodocs'],
        parameters: {
            layout: 'centered'
        },
        args: {
            name: 'prompts',
            required: true,
            isMissing: false,
            description: 'Prompt to segment with and the label to assign to the masks.',
            onUpdate: fn()
        },
        argTypes: {
            name: {
                description: 'Parameter name. Used as the label and as the `data-testid` prefix.',
                control: 'text'
            },
            value: {
                description:
                    'Current rows. Each row maps every column name to a cell of that column ' +
                    'type: a string, a number, or a boolean for a `bool` column.',
                control: 'object'
            },
            columns: {
                description:
                    'Columns in display order, taken from the parameter definition. Each column ' +
                    'carries its name, description, default, required flag and the Python type ' +
                    'name that decides how its cells are rendered.',
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

<script lang="ts">
    import { column } from '../fixtures';

    // `column()` already describes a required `str` column named `prompt`.
    const COLUMNS = [
        column({ description: 'What to segment in the image.' }),
        column({
            name: 'label',
            description: 'Label to assign to the resulting masks.',
            default: 'pedestrian',
            required: false
        })
    ];

    // A column can hold any built-in parameter type, so cells are not always text inputs.
    const MIXED_COLUMNS = [
        column({ description: 'What to segment in the image.' }),
        column({
            name: 'threshold',
            description: 'Minimum confidence to keep a mask.',
            paramType: 'float',
            default: 0.5,
            required: false
        }),
        column({
            name: 'enabled',
            description: 'Whether to run this prompt at all.',
            paramType: 'bool',
            default: true,
            required: false
        })
    ];

    // More columns than the dialog can show at once, spanning every cell type.
    const WIDE_COLUMNS = [
        column({ description: 'What to segment in the image.' }),
        column({
            name: 'label',
            description: 'Label to assign to the resulting masks.',
            default: 'pedestrian',
            required: false
        }),
        column({
            name: 'limit',
            description: 'Most masks to keep per image.',
            paramType: 'int',
            default: 5,
            required: false
        }),
        column({
            name: 'threshold',
            description: 'Minimum confidence to keep a mask.',
            paramType: 'float',
            default: 0.5,
            required: false
        }),
        column({
            name: 'enabled',
            description: 'Whether to run this prompt at all.',
            paramType: 'bool',
            default: true,
            required: false
        })
    ];

    const WIDE_ROW = {
        prompt: 'person',
        label: 'pedestrian',
        limit: 5,
        threshold: 0.5,
        enabled: true
    };
</script>

<!-- The table fills whatever width it is given, so every story renders at the width it would have in
     the operator dialog: max-w-md (28rem) less the dialog's own p-6. Without this the stories size to
     their content and the scrolling ones never overflow. -->
{#snippet dialogWidth(args)}
    <div class="w-[25rem]">
        <ParameterTable {...args} />
    </div>
{/snippet}

<Story name="Empty" args={{ value: [], columns: COLUMNS }} template={dialogWidth} />

<Story
    name="With rows"
    args={{
        value: [
            { prompt: 'person', label: 'pedestrian' },
            { prompt: 'car', label: 'vehicle' }
        ],
        columns: COLUMNS
    }}
    template={dialogWidth}
/>

<Story
    name="Incomplete row (invalid)"
    args={{ value: [{ prompt: '', label: 'pedestrian' }], columns: COLUMNS, isMissing: true }}
    template={dialogWidth}
/>

<!-- Rows only start scrolling past four of them, so seven exercises the vertical scroll. The header
     stays pinned to the top of the box while they scroll. -->
<Story
    name="Many rows (scrolling)"
    args={{
        value: [
            { prompt: 'person', label: 'pedestrian' },
            { prompt: 'car', label: 'vehicle' },
            { prompt: 'dog', label: 'animal' },
            { prompt: 'tree', label: 'plant' },
            { prompt: 'bicycle', label: 'vehicle' },
            { prompt: 'traffic light', label: 'signal' },
            { prompt: 'building', label: 'structure' }
        ],
        columns: COLUMNS
    }}
    template={dialogWidth}
/>

<!-- A `float` column renders a number input and a `bool` column a checkbox. -->
<Story
    name="Mixed column types"
    args={{
        value: [
            { prompt: 'person', threshold: 0.5, enabled: true },
            { prompt: 'car', threshold: 0.8, enabled: false }
        ],
        columns: MIXED_COLUMNS
    }}
    template={dialogWidth}
/>

<!-- Columns stop shrinking at 9rem, so past two of them the table scrolls sideways rather than
     squeezing the cells. The header scrolls with the rows while the remove button stays pinned to the
     right edge. -->
<Story
    name="Many columns (horizontal scroll)"
    args={{
        value: [WIDE_ROW, { ...WIDE_ROW, prompt: 'car', label: 'vehicle', enabled: false }],
        columns: WIDE_COLUMNS
    }}
    template={dialogWidth}
/>

<!-- Both axes at once: the header stays pinned to the top, the remove button to the right, and the
     corner where the two meet stays covered. -->
<Story
    name="Many columns and rows (both scrollbars)"
    args={{
        value: [
            WIDE_ROW,
            { ...WIDE_ROW, prompt: 'car', label: 'vehicle', enabled: false },
            { ...WIDE_ROW, prompt: 'dog', label: 'animal', limit: 2 },
            { ...WIDE_ROW, prompt: 'tree', label: 'plant', threshold: 0.9 },
            { ...WIDE_ROW, prompt: 'bicycle', label: 'vehicle', enabled: false },
            { ...WIDE_ROW, prompt: 'traffic light', label: 'signal', limit: 1 },
            { ...WIDE_ROW, prompt: 'building', label: 'structure' }
        ],
        columns: WIDE_COLUMNS
    }}
    template={dialogWidth}
/>

<Story
    name="Single column"
    args={{
        name: 'classes',
        value: [{ class: 'person' }, { class: 'car' }],
        columns: [column({ name: 'class', description: 'Class to keep.' })],
        required: false,
        description: undefined
    }}
    template={dialogWidth}
/>
