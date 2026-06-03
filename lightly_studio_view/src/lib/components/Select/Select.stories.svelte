<script module lang="ts">
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import { Crosshair, Plus, Sigma, Target, TrendingUp } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import Select from './Select.svelte';

    const DEMO_ITEMS = [
        { value: 'accuracy', label: 'Accuracy' },
        { value: 'precision', label: 'Precision' },
        { value: 'recall', label: 'Recall' },
        { value: 'f1', label: 'F1 Score' }
    ];

    const DEMO_ITEMS_WITH_ICONS = [
        { value: 'accuracy', label: 'Accuracy', icon: Target },
        { value: 'precision', label: 'Precision', icon: Crosshair },
        { value: 'recall', label: 'Recall', icon: TrendingUp },
        { value: 'f1', label: 'F1 Score', icon: Sigma }
    ];

    const { Story } = defineMeta({
        title: 'Components/Primitives/Select',
        component: Select,
        tags: ['autodocs'],
        parameters: {
            layout: 'centered'
        },
        argTypes: {
            items: {
                description:
                    'List of items to render. Mutually exclusive with the `children` slot.',
                control: 'object'
            },
            value: {
                description: 'Currently selected value.',
                control: 'select',
                options: ['', 'accuracy', 'precision', 'recall', 'f1']
            },
            placeholder: {
                description: 'Placeholder text shown when nothing is selected.',
                control: 'text',
                table: {
                    type: { summary: 'string' },
                    defaultValue: { summary: 'Select…' }
                }
            },
            allowDeselect: {
                description: 'Allow clearing the current selection.',
                control: 'boolean',
                table: {
                    type: { summary: 'boolean' },
                    defaultValue: { summary: 'false' }
                }
            },
            disabled: {
                description: 'Whether the select is disabled.',
                control: 'boolean',
                table: {
                    type: { summary: 'boolean' },
                    defaultValue: { summary: 'false' }
                }
            },
            size: {
                description: 'Trigger size. Heights align with the Button primitive.',
                control: 'select',
                options: ['sm', 'md', 'lg'],
                table: {
                    type: { summary: "'sm' | 'md' | 'lg'" },
                    defaultValue: { summary: 'md' }
                }
            },
            class: {
                description: 'Additional class names for the trigger button.',
                control: 'text'
            },
            testId: {
                description: '`data-testid` for the trigger element.',
                control: 'text'
            },
            onValueChange: {
                description: 'Called when the selected value changes.',
                control: false
            },
            children: {
                description:
                    'Advanced slot: provide custom `Select.Item` / `Select.Group` markup. When provided, `items` is ignored.',
                control: false
            }
        }
    });
</script>

<Story
    name="NoSelection"
    args={{
        items: DEMO_ITEMS,
        placeholder: 'Pick a metric…',
        onValueChange: fn()
    }}
/>

<Story
    name="PreSelected"
    args={{
        items: DEMO_ITEMS,
        value: 'precision',
        placeholder: 'Pick a metric…',
        onValueChange: fn()
    }}
/>

<Story
    name="WithDeselect"
    args={{
        items: DEMO_ITEMS,
        value: 'recall',
        allowDeselect: true,
        placeholder: 'Pick a metric…',
        onValueChange: fn()
    }}
/>

<Story
    name="WithButton"
    args={{
        items: DEMO_ITEMS,
        value: 'precision',
        placeholder: 'Pick a metric…',
        onValueChange: fn()
    }}
>
    {#snippet template(args)}
        <div class="flex items-center gap-2">
            <Select {...args} />
            <Button variant="ghost" icon={Plus} buttonProps={{ onclick: fn() }}>Add metric</Button>
        </div>
    {/snippet}
</Story>

<Story
    name="Sizes"
    args={{
        items: DEMO_ITEMS,
        value: 'precision',
        placeholder: 'Pick a metric…',
        onValueChange: fn()
    }}
>
    {#snippet template(args)}
        <div class="flex items-center gap-2">
            <Select {...args} size="sm" />
            <Select {...args} size="md" />
            <Select {...args} size="lg" />
        </div>
    {/snippet}
</Story>

<Story
    name="WithIcons"
    args={{
        items: DEMO_ITEMS_WITH_ICONS,
        value: 'precision',
        placeholder: 'Pick a metric…',
        onValueChange: fn()
    }}
/>

<Story
    name="WithIconsNoSelection"
    args={{
        items: DEMO_ITEMS_WITH_ICONS,
        placeholder: 'Pick a metric…',
        onValueChange: fn()
    }}
/>
