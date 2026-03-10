<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import Badge from './badge.svelte';

    const { Story } = defineMeta({
        title: 'Components/UI/Badge',
        component: Badge,
        tags: ['autodocs'],
        argTypes: {
            variant: {
                control: 'select',
                options: ['default', 'secondary', 'destructive', 'outline']
            }
        }
    });
</script>

<Story name="Default" args={{ variant: 'default' }}>Badge</Story>

<Story name="Secondary" args={{ variant: 'secondary' }}>Badge</Story>

<Story name="Destructive" args={{ variant: 'destructive' }}>Badge</Story>

<Story name="Outline" args={{ variant: 'outline' }}>Badge</Story>
