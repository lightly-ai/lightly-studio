<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import GridItem from './GridItem.svelte';

    const { Story } = defineMeta({
        title: 'Components/GridItem',
        component: GridItem,
        tags: ['autodocs'],
        argTypes: {
            width: { control: 'number', defaultValue: 200 },
            height: { control: 'number', defaultValue: 200 }
        }
    });
</script>

<Story name="With Image">
    <img src="https://picsum.photos/200" alt="Placeholder" class="h-full w-full object-cover" />
</Story>
