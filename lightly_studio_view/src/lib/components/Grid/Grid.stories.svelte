<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import Grid from './Grid.svelte';
    import GridItem from '../GridItem/GridItem.svelte';
    import { fn } from 'storybook/test';

    const { Story } = defineMeta({
        component: Grid,
        title: 'Components/Grid',
        tags: ['autodocs']
    });
</script>

<Story
    name="Base example"
    args={{
        itemCount: 100,
        gridProps: {
            scrollPosition: 400,
            onscroll: fn()
        }
    }}
>
    {#snippet template(args)}
        <Grid {...args}>
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
    {/snippet}
</Story>

<Story name="With footer" args={{ itemCount: 100, onScroll: fn() }}>
    {#snippet template(args)}
        <Grid {...args}>
            {#snippet gridItem({ index, style, width, height })}
                <GridItem {width} {height} containerProps={{ style }}>
                    <img
                        src="https://picsum.photos/180?random={index}"
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
    {/snippet}
</Story>
