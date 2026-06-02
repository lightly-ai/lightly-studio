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
        },
        argTypes: {
            variant: {
                description: 'Visual style of the button. Maps to the shadcn button variants.',
                control: 'select',
                options: ['default', 'destructive', 'outline', 'secondary', 'ghost', 'link'],
                table: {
                    type: {
                        summary:
                            "'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'"
                    },
                    defaultValue: { summary: 'default' }
                }
            },
            collapseAt: {
                description:
                    'Hide the label at and below the given Tailwind breakpoint while keeping the icon visible. `never` keeps the label at all sizes.',
                control: 'select',
                options: ['sm', 'md', 'lg', 'xl', '2xl', 'never']
            },
            isPending: {
                description:
                    'When true, disables the button and shows an indeterminate linear progress bar at the bottom.',
                control: 'boolean'
            },
            icon: {
                description: 'Lucide icon component rendered before the label.',
                control: false
            },
            buttonProps: {
                description:
                    'Props forwarded to the underlying shadcn button element (e.g. `onclick`, `disabled`, `title`, `type`, `class`).',
                control: 'object'
            },
            children: {
                description: 'Button label content. Omit for an icon-only button.',
                control: false
            }
        }
    });
</script>

<Story name="Minimal">Click me</Story>

<Story name="With Icon" args={{ icon: Pencil, buttonProps: { onclick: fn() } }}>
    Edit Annotations
</Story>

<Story name="IconOnly" args={{ icon: Plus, buttonProps: { onclick: fn() } }} />
