<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import ParameterTable from './ParameterTable.svelte';

    const { Story } = defineMeta({
        title: 'Components/Operator/ParameterTable',
        component: ParameterTable,
        tags: ['autodocs'],
        parameters: { layout: 'centered' },
        args: {
            name: 'prompts',
            required: true,
            isMissing: false,
            description: 'Prompt to segment with and the label to assign to the masks.',
            onUpdate: fn()
        }
    });
</script>

<script lang="ts">
    import { column } from '../fixtures';
    import { promptColumns, promptRows, wideColumns, wideRows } from './storyFixtures';
</script>

<!-- The table fills whatever width it is given, so every story renders at the width it would have in
     the operator dialog: max-w-md (28rem) less the dialog's own p-6. Without this the stories size to
     their content and the scrolling ones never overflow. -->
{#snippet dialogWidth(args)}
    <div class="w-[25rem]">
        <ParameterTable {...args} />
    </div>
{/snippet}

<Story name="Empty" args={{ value: [], columns: promptColumns }} template={dialogWidth} />

<Story
    name="With rows"
    args={{ value: promptRows.slice(0, 2), columns: promptColumns }}
    template={dialogWidth}
/>

<Story
    name="Incomplete row (invalid)"
    args={{ value: [{ prompt: '', label: 'pedestrian' }], columns: promptColumns, isMissing: true }}
    template={dialogWidth}
/>

<!-- The header stays pinned to the top of the box while the rows scroll. -->
<Story
    name="Many rows (scrolling)"
    args={{ value: promptRows, columns: promptColumns }}
    template={dialogWidth}
/>

<!-- Columns stop shrinking at 9rem, so past two of them the table scrolls sideways rather than
     squeezing the cells. A `float` column renders a number input and a `bool` column a checkbox. -->
<Story
    name="Many columns (horizontal scroll)"
    args={{ value: wideRows.slice(0, 2), columns: wideColumns }}
    template={dialogWidth}
/>

<!-- Both axes at once: the header stays pinned to the top, the remove button to the right, and the
     corner where the two meet stays covered. -->
<Story
    name="Many columns and rows (both scrollbars)"
    args={{ value: wideRows, columns: wideColumns }}
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
