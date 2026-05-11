<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import MenuItem from './MenuItem.svelte';
    import { fn } from 'storybook/test';

    const { Story } = defineMeta({
        title: 'Components/SideMenu/MenuItem',
        component: MenuItem,
        tags: ['autodocs'],
        argTypes: {
            name: { control: 'text' },
            checked: { control: 'boolean' },
            showColorMarker: { control: 'boolean', defaultValue: false }
        }
    });
</script>

<Story
    name="Default"
    args={{
        name: 'Example Label',
        checked: false,
        onCheckedChange: fn()
    }}
/>
