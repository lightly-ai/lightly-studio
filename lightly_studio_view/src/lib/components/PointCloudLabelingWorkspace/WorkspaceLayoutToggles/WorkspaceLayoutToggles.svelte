<script lang="ts">
    import type { Component } from 'svelte';
    import type { IconProps } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { cn } from '$lib/utils';

    export interface LayoutToggle {
        id: string;
        /** The panel name, used for the tooltip and the accessible name. */
        label: string;
        icon: Component<IconProps>;
        /** Whether the panel shows; the toggle is highlighted then. */
        isActive: boolean;
    }

    /** Icon toggles that show or hide the workspace panels, like the layout controls of VS Code. */
    interface Props {
        toggles: readonly LayoutToggle[];
        onToggle: (id: string) => void;
    }

    let { toggles, onToggle }: Props = $props();
</script>

<div class="flex items-center gap-0.5" role="group" aria-label="Workspace layout">
    {#each toggles as toggle (toggle.id)}
        <Button
            variant="ghost"
            icon={toggle.icon}
            ariaLabel={toggle.label}
            buttonProps={{
                type: 'button',
                size: 'xs',
                title: `${toggle.isActive ? 'Hide' : 'Show'} ${toggle.label.toLowerCase()}`,
                'aria-pressed': toggle.isActive,
                class: cn(
                    'h-8 w-8 p-0',
                    toggle.isActive
                        ? 'bg-accent text-foreground'
                        : 'text-muted-foreground hover:bg-accent/40'
                ),
                onclick: () => onToggle(toggle.id)
            }}
        />
    {/each}
</div>
