<script module>
    /**
     * Storybook for the shared Button component.
     *
     * The Button wraps a native <button> (or <a> when `href` is set) and exposes
     * two axes of control:
     *
     *   variant — controls colour / fill intent
     *     default    primary filled action (e.g. "Create", "Save")
     *     secondary  muted fill — used for active/on toggle state
     *     outline    bordered, no fill — used for inactive toggle state and secondary actions
     *     ghost      transparent — used for toolbar icon buttons and low-emphasis actions
     *     destructive  destructive filled action (e.g. "Delete")
     *     link       looks like an inline hyperlink
     *
     *   size — controls height and padding
     *     default  h-10  standard form / dialog buttons
     *     sm       h-9   compact toolbar buttons with text
     *     icon     h-10 w-10  square icon-only buttons
     *
     * Toggle (active) pattern
     * -----------------------
     * There is no separate "toggle" component. Use variant="outline" for the
     * inactive state and variant="secondary" for the active/on state, both with
     * size="sm". See the "Toggle – inactive / active" story below for the
     * canonical example (used by the Embeddings and Evaluation panel buttons).
     */
    import { defineMeta } from '@storybook/addon-svelte-csf';
    import { fn } from 'storybook/test';
    import {
        ChartNetwork,
        Check,
        ChevronRight,
        Gauge,
        Pencil,
        Plus,
        Trash2,
        X
    } from '@lucide/svelte';
    import Button from './button.svelte';

    const { Story } = defineMeta({
        title: 'Components/UI/Button',
        component: Button,
        tags: ['autodocs'],
        argTypes: {
            variant: {
                control: 'select',
                options: ['default', 'secondary', 'outline', 'ghost', 'destructive', 'link']
            },
            size: {
                control: 'select',
                options: ['default', 'sm', 'icon']
            },
            disabled: { control: 'boolean' }
        },
        args: { onclick: fn() }
    });
</script>

<!-- ─────────────────────────────────────────────
     1. Variant showcase
───────────────────────────────────────────── -->

<Story name="Default (primary)" args={{ variant: 'default', size: 'default' }}>
    {#snippet children()}
        Save changes
    {/snippet}
</Story>

<Story name="Secondary" args={{ variant: 'secondary', size: 'default' }}>
    {#snippet children()}
        Secondary action
    {/snippet}
</Story>

<Story name="Outline" args={{ variant: 'outline', size: 'default' }}>
    {#snippet children()}
        Cancel
    {/snippet}
</Story>

<Story name="Ghost" args={{ variant: 'ghost', size: 'default' }}>
    {#snippet children()}
        Ghost action
    {/snippet}
</Story>

<Story name="Destructive" args={{ variant: 'destructive', size: 'default' }}>
    {#snippet children()}
        Delete
    {/snippet}
</Story>

<Story name="Link" args={{ variant: 'link', size: 'default' }}>
    {#snippet children()}
        Learn more
    {/snippet}
</Story>

<!-- ─────────────────────────────────────────────
     2. All variants side by side
───────────────────────────────────────────── -->
<Story name="All variants" asChild>
    <div class="flex flex-wrap items-center gap-3 p-6">
        <Button variant="default" onclick={fn()}>Default</Button>
        <Button variant="secondary" onclick={fn()}>Secondary</Button>
        <Button variant="outline" onclick={fn()}>Outline</Button>
        <Button variant="ghost" onclick={fn()}>Ghost</Button>
        <Button variant="destructive" onclick={fn()}>Destructive</Button>
        <Button variant="link" onclick={fn()}>Link</Button>
    </div>
</Story>

<!-- ─────────────────────────────────────────────
     3. Sizes
───────────────────────────────────────────── -->
<Story name="Sizes" asChild>
    <div class="flex flex-wrap items-center gap-3 p-6">
        <Button variant="outline" size="default" onclick={fn()}>Default (h-10)</Button>
        <Button variant="outline" size="sm" onclick={fn()}>Small (h-9)</Button>
        <Button variant="outline" size="icon" aria-label="Add" onclick={fn()}>
            <Plus />
        </Button>
    </div>
</Story>

<!-- ─────────────────────────────────────────────
     4. With icon + label
     Reference: toolbar buttons that combine an icon with a short label
     (e.g. Embeddings, Evaluation, Edit Annotations)
───────────────────────────────────────────── -->
<Story name="Icon + label (default)" args={{ variant: 'default', size: 'default' }}>
    {#snippet children()}
        <Pencil />
        Edit annotations
    {/snippet}
</Story>

<Story name="Icon + label (sm / toolbar)" asChild>
    <div class="flex flex-wrap items-center gap-2 p-6">
        <Button variant="outline" size="sm" onclick={fn()}>
            <ChartNetwork />
            Embeddings
        </Button>
        <Button variant="outline" size="sm" onclick={fn()}>
            <Gauge />
            Evaluation
        </Button>
        <Button variant="default" size="sm" onclick={fn()}>
            <Pencil />
            Edit annotations
        </Button>
    </div>
</Story>

<Story name="Icon + label (trailing icon)" args={{ variant: 'outline', size: 'default' }}>
    {#snippet children()}
        Continue
        <ChevronRight />
    {/snippet}
</Story>

<!-- ─────────────────────────────────────────────
     5. Icon-only buttons
───────────────────────────────────────────── -->
<Story name="Icon-only" asChild>
    <div class="flex items-center gap-2 p-6">
        <Button variant="ghost" size="icon" aria-label="Add" onclick={fn()}>
            <Plus />
        </Button>
        <Button variant="ghost" size="icon" aria-label="Edit" onclick={fn()}>
            <Pencil />
        </Button>
        <Button variant="outline" size="icon" aria-label="Confirm" onclick={fn()}>
            <Check />
        </Button>
        <Button variant="destructive" size="icon" aria-label="Delete" onclick={fn()}>
            <Trash2 />
        </Button>
        <Button variant="ghost" size="icon" aria-label="Close" onclick={fn()}>
            <X />
        </Button>
    </div>
</Story>

<!-- ─────────────────────────────────────────────
     6. Toggle (active / inactive) pattern
     Use variant="outline" for off, variant="secondary" for on.
     Always size="sm" in the toolbar.
───────────────────────────────────────────── -->
<Story name="Toggle – inactive" args={{ variant: 'outline', size: 'sm' }}>
    {#snippet children()}
        <ChartNetwork />
        Embeddings
    {/snippet}
</Story>

<Story name="Toggle – active" args={{ variant: 'secondary', size: 'sm' }}>
    {#snippet children()}
        <ChartNetwork />
        Embeddings
    {/snippet}
</Story>

<Story name="Toggle – side by side" asChild>
    <div class="flex items-center gap-2 p-6">
        <!-- inactive -->
        <Button variant="outline" size="sm" onclick={fn()}>
            <ChartNetwork />
            Embeddings
        </Button>
        <!-- active -->
        <Button variant="secondary" size="sm" onclick={fn()}>
            <Gauge />
            Evaluation
        </Button>
    </div>
</Story>

<!-- ─────────────────────────────────────────────
     7. Disabled states
───────────────────────────────────────────── -->
<Story name="Disabled" asChild>
    <div class="flex flex-wrap items-center gap-3 p-6">
        <Button variant="default" disabled onclick={fn()}>Save changes</Button>
        <Button variant="outline" disabled onclick={fn()}>Cancel</Button>
        <Button variant="ghost" size="icon" disabled aria-label="Edit" onclick={fn()}>
            <Pencil />
        </Button>
        <Button variant="destructive" disabled onclick={fn()}>Delete</Button>
    </div>
</Story>
