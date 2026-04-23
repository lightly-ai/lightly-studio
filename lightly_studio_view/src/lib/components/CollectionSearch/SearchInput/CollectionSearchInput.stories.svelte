<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import CollectionSearchInput from './CollectionSearchInput.svelte';
    import { fn } from 'storybook/test';

    const { Story } = defineMeta({
        title: 'Components/CollectionSearch/CollectionSearchInput',
        component: CollectionSearchInput,
        tags: ['autodocs']
    });
</script>

<Story
    name="Default"
    args={{
        value: '',
        inputProps: {
            placeholder: 'Search samples by description or image',
            onkeydown: fn(),
            onpaste: fn()
        },
        onUploadClick: fn()
    }}
>
    {#snippet template(args)}
        <div class="space-y-2">
            <CollectionSearchInput bind:value={args.value} {...args} />
            <p class="text-xs text-muted-foreground">
                Current value: <span class="font-mono">{args.value || '(empty)'}</span>
            </p>
        </div>
    {/snippet}
</Story>
