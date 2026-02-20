<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import GridItem from './GridItem.svelte';

    const { Story } = defineMeta({
        title: 'Components/GridItem',
        component: GridItem,
        tags: ['autodocs'],
        argTypes: {
            width: { control: 'text' },
            height: { control: 'text' }
        }
    });
</script>

<Story name="Default" args={{ width: 200, height: 200 }}>
    {#snippet children()}
        <div>Grid Item Content</div>
    {/snippet}
</Story>

<Story name="With Image" args={{ width: 200, height: 200 }}>
    {#snippet children()}
        <img src="https://picsum.photos/200" alt="Placeholder" class="h-full w-full object-cover" />
    {/snippet}
</Story>

<Story name="With Custom Content" args={{ width: 200, height: 200 }}>
    {#snippet children()}
        <div class="flex h-full flex-col items-center justify-center bg-blue-500 p-4 text-white">
            <h3 class="font-bold">Custom Item</h3>
            <p class="text-sm">This is a custom grid item</p>
        </div>
    {/snippet}
</Story>

<Story name="Small Size" args={{ width: 100, height: 100 }}>
    {#snippet children()}
        <div class="flex h-full items-center justify-center bg-purple-200 text-xs">Small</div>
    {/snippet}
</Story>

<Story name="Large Size" args={{ width: 300, height: 300 }}>
    {#snippet children()}
        <img src="https://picsum.photos/300" alt="Large" class="h-full w-full object-cover" />
    {/snippet}
</Story>
