<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import FilterChip from './FilterChip.svelte';

    const { Story } = defineMeta({
        title: 'Components/FilterChip',
        component: FilterChip,
        tags: ['autodocs'],
        argTypes: {
            checked: { control: 'boolean' },
            title: { control: 'text' },
            checkboxLabel: { control: 'text' }
        }
    });
</script>

<Story
    name="Default"
    args={{
        checked: true,
        title: 'Has prediction',
        checkboxLabel: 'Toggle has prediction filter',
        onCheckedChange: fn(),
        onClear: fn()
    }}
/>

<Story
    name="WithSubtitle"
    args={{
        checked: true,
        title: 'Category Filter',
        checkboxLabel: 'Toggle category filter',
        onCheckedChange: fn(),
        onClear: fn(),
        onclick: fn()
    }}
>
    {#snippet template(args)}
        <FilterChip {...args}>
            {#snippet subtitle()}
                <div class="text-xs text-muted-foreground">Selected 14 categories</div>
            {/snippet}
        </FilterChip>
    {/snippet}
</Story>
