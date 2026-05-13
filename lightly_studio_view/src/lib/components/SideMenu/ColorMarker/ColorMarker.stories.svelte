<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import ColorMarker from './ColorMarker.svelte';

    const { Story } = defineMeta({
        title: 'Components/SideMenu/ColorMarker',
        component: ColorMarker,
        tags: ['autodocs'],
        argTypes: {
            label: { control: 'text', defaultValue: 'Example Label' }
        }
    });
</script>

<Story
    name="Default"
    args={{
        label: 'Example Label'
    }}
/>
