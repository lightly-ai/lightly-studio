<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import { Pencil, Check, Undo2, Plus, Trash2 } from '@lucide/svelte';
    import Button from './Button.svelte';

    const { Story } = defineMeta({
        title: 'Components/Primitives/Button',
        component: Button,
        tags: ['autodocs'],
        parameters: {
            layout: 'centered'
        }
    });
</script>

<Story name="Minimal">Click me</Story>

<Story name="Default" args={{ icon: Pencil, buttonProps: { onclick: fn() } }}>
    Edit Annotations
</Story>

<Story name="Ghost" args={{ variant: 'ghost', icon: Pencil, buttonProps: { onclick: fn() } }}
    >Edit Annotations</Story
>

<Story name="Outline" args={{ icon: Pencil, variant: 'outline', buttonProps: { onclick: fn() } }}>
    Edit Annotations
</Story>

<Story
    name="Destructive"
    args={{ icon: Trash2, variant: 'destructive', buttonProps: { onclick: fn() } }}
>
    Delete
</Story>

<Story
    name="Disabled"
    args={{
        icon: Undo2,
        variant: 'outline',
        buttonProps: { disabled: true, onclick: fn() }
    }}
>
    Undo
</Story>

<Story name="WithoutIcon" args={{ buttonProps: { onclick: fn() } }}>Finish Editing</Story>

<Story name="IconOnly" args={{ icon: Plus, buttonProps: { onclick: fn() } }} />

<Story
    name="FinishEditing"
    args={{
        icon: Check,
        buttonProps: { onclick: fn(), title: 'Finish Editing' }
    }}
>
    Finish Editing
</Story>

<Story name="Pending" args={{ icon: Check, isPending: true, buttonProps: { onclick: fn() } }}>
    Saving
</Story>
