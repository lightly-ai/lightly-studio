<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import LayoutCard from './LayoutCard.svelte';

    const { Story } = defineMeta({
        title: 'Components/LayoutCard',
        component: LayoutCard,
        tags: ['autodocs'],
        argTypes: {
            className: { control: 'text' }
        }
    });
</script>

<Story name="Default">
    <h2 class="text-xl font-semibold">Card Title</h2>
    <p>This is a basic layout card with some content inside.</p>
</Story>

<Story name="With Complex Content">
    <h2 class="text-2xl font-bold">Dashboard</h2>
    <div class="space-y-4">
        <div class="rounded bg-muted p-4">
            <h3 class="font-semibold">Section 1</h3>
            <p class="text-sm text-muted-foreground">Some description text here.</p>
        </div>
        <div class="rounded bg-muted p-4">
            <h3 class="font-semibold">Section 2</h3>
            <p class="text-sm text-muted-foreground">Another section with content.</p>
        </div>
    </div>
</Story>

<Story name="Custom ClassName" args={{ className: 'border-2 border-primary' }}>
    <h2 class="text-xl font-semibold">Custom Styled Card</h2>
    <p>This card has a custom border applied via the className prop.</p>
</Story>

<Story name="Minimal Content">
    <p class="text-center text-muted-foreground">Empty state</p>
</Story>
