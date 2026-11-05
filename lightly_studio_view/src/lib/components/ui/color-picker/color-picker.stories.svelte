<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import ColorPicker from './color-picker.svelte';

    const { Story } = defineMeta({
        title: 'Components/Primitives/ColorPicker',
        component: ColorPicker,
        tags: ['autodocs'],
        parameters: {
            layout: 'centered'
        },
        args: {
            initialColor: '#3b82f6',
            initialAlpha: 1,
            triggerLabel: 'Change color',
            onChange: fn(),
            onClose: fn()
        },
        argTypes: {
            initialColor: {
                description: 'Color shown when the picker opens, as a hex string.',
                control: 'color'
            },
            initialAlpha: {
                description: 'Opacity shown when the picker opens, from 0 to 1.',
                control: { type: 'range', min: 0, max: 1, step: 0.01 }
            },
            position: {
                description: 'Side of the trigger where the picker opens.',
                control: 'select',
                options: ['top', 'bottom', 'left', 'right']
            },
            triggerLabel: {
                description: 'Accessible label of the trigger button.',
                control: 'text'
            }
        }
    });
</script>

<Story name="Default">
    {#snippet template(args)}
        <ColorPicker {...args}>
            <span class="block h-6 w-6 rounded border" style="background-color: {args.initialColor}"></span>
        </ColorPicker>
    {/snippet}
</Story>

<Story name="Semi-transparent" args={{ initialColor: '#22c55e', initialAlpha: 0.4 }}>
    {#snippet template(args)}
        <ColorPicker {...args}>
            <span class="block h-6 w-6 rounded border" style="background-color: {args.initialColor}"></span>
        </ColorPicker>
    {/snippet}
</Story>

<Story name="Opens Below" args={{ position: 'bottom' }}>
    {#snippet template(args)}
        <ColorPicker {...args}>
            <span class="block h-6 w-6 rounded border" style="background-color: {args.initialColor}"></span>
        </ColorPicker>
    {/snippet}
</Story>
