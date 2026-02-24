<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import Grid from './Grid.svelte';
    import GridItem from '../GridItem/GridItem.svelte';

    const { Story } = defineMeta({
        title: 'Components/Grid',
        tags: ['autodocs']
    });
</script>

<Story name="Base example" asChild>
    <Grid itemCount={100} columnCount={6}>
        {#snippet gridItem({ index, style, width, height })}
            <GridItem {width} {height} containerProps={{ style }}>
                <img
                    src="https://picsum.photos/180?random={index}"
                    alt="Placeholder {index + 1}"
                    class="h-full w-full object-cover"
                />
            </GridItem>
        {/snippet}
    </Grid>
</Story>

<Story name="With many columns" asChild>
    <Grid itemCount={200} columnCount={10}>
        {#snippet gridItem({ index, style, width, height })}
            <GridItem {width} {height} containerProps={{ style }}>
                <img
                    src="https://picsum.photos/150?random={index + 200}"
                    alt="Placeholder {index + 1}"
                    class="h-full w-full object-cover"
                />
            </GridItem>
        {/snippet}
    </Grid>
</Story>

<Story name="With footer" asChild>
    <Grid itemCount={60} columnCount={4}>
        {#snippet gridItem({ index, style, width, height })}
            <GridItem {width} {height} containerProps={{ style }}>
                <img
                    src="https://picsum.photos/190?random={index + 500}"
                    alt="Placeholder {index + 1}"
                    class="h-full w-full object-cover"
                />
            </GridItem>
        {/snippet}
        {#snippet footerItem()}
            <div class="bg-gray-200 p-4 text-center text-gray-700">
                End of grid - 60 items loaded
            </div>
        {/snippet}
    </Grid>
</Story>

<Story name="Large dataset" asChild>
    <Grid itemCount={10000} columnCount={8}>
        {#snippet gridItem({ index, style, width, height })}
            <GridItem {width} {height} containerProps={{ style }}>
                <div
                    class="flex h-full w-full items-center justify-center bg-gradient-to-br from-blue-400 to-purple-500 font-bold text-white"
                >
                    {index + 1}
                </div>
            </GridItem>
        {/snippet}
    </Grid>
</Story>
