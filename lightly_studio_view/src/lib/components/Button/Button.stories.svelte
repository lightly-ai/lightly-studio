<script module>
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import { ChevronDown, Pencil, Plus } from '@lucide/svelte';
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
            iconAfter: {
                description: 'Lucide icon component rendered after the label.',
                control: false
            },
            iconAfterClass: {
                description: 'Additional class applied to the trailing icon (merged with `size-4`).',
                control: 'text'
            },
            buttonProps: {
                description:
                    'Props forwarded to the underlying shadcn button element (e.g. `onclick`, `disabled`, `title`, `type`, `class`).',
                control: 'object'
            },
            children: {
                description: 'Button label content. Omit for an icon-only button.',
                control: false
            },
            ariaLabel: {
                description:
                    'Accessible name for the button. Required for icon-only buttons (no `children`); optional when a label is provided.',
                control: 'text'
            }
        }
    });
</script>

<Story name="Minimal">Click me</Story>

<Story name="With Icon" args={{ icon: Pencil, buttonProps: { onclick: fn() } }}>
    Edit Annotations
</Story>

<Story name="With Icon After" args={{ iconAfter: ChevronDown, buttonProps: { onclick: fn() } }}>
    Open menu
</Story>

<Story
    name="IconOnly"
    args={{ icon: Plus, ariaLabel: 'Add item', buttonProps: { onclick: fn() } }}
/>
