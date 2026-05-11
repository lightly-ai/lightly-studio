<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { SideMenu } from '..';
    import { fn } from 'storybook/test';

    const { Story } = defineMeta({
        title: 'Components/SideMenu/SideMenu',
        component: SideMenu,
        tags: ['autodocs'],
        argTypes: {
            items: { control: 'object' },
            onChangeSelectedItems: { action: 'onChangeSelectedItems' }
        }
    });
</script>

<Story
    name="Default"
    args={{
        items: [
            { id: '1', name: 'Annotation Collection A' },
            { id: '2', name: 'Annotation Collection B' },
            { id: '3', name: 'Annotation Collection C' }
        ],
        onChangeSelectedItems: fn()
    }}
/>

<Story
    name="WithPreselected"
    args={{
        items: [
            { id: '1', name: 'Annotation Collection A' },
            { id: '2', name: 'Annotation Collection B' },
            { id: '3', name: 'Annotation Collection C' }
        ],
        initialSelectedItemsIds: ['1', '3'],
        onChangeSelectedItems: fn()
    }}
/>

<Story
    name="With Color Marker"
    args={{
        items: [
            { id: '1', name: 'Annotation Collection A' },
            { id: '2', name: 'Annotation Collection B' },
            { id: '3', name: 'Annotation Collection C' }
        ],
        initialSelectedItemsIds: ['1', '3'],
        showColorMarker: true,
        onChangeSelectedItems: fn()
    }}
/>

<Story
    name="Empty"
    args={{
        items: [],
        onChangeSelectedItems: fn()
    }}
/>
