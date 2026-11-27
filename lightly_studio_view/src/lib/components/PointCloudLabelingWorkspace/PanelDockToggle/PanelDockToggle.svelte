<script lang="ts" module>
    /** The workspace edge a panel sits at: below the scene or on its right. */
    export type PanelDock = 'bottom' | 'right';
</script>

<script lang="ts">
    import PanelBottom from '@lucide/svelte/icons/panel-bottom';
    import PanelRight from '@lucide/svelte/icons/panel-right';
    import { Button } from '$lib/components';

    /** Moves a panel between the bottom and the right of the scene; the icon shows the target. */
    interface Props {
        dock: PanelDock;
        /** The panel name, used in the button label. */
        label: string;
        onChange: (dock: PanelDock) => void;
    }

    let { dock, label, onChange }: Props = $props();
    const isBottom = $derived(dock === 'bottom');
    const ariaLabel = $derived(`Show ${label} ${isBottom ? 'on the right' : 'at the bottom'}`);
</script>

<Button
    variant="ghost"
    icon={isBottom ? PanelRight : PanelBottom}
    {ariaLabel}
    buttonProps={{
        type: 'button',
        size: 'xs',
        class: 'h-7 w-7 p-0',
        title: ariaLabel,
        onclick: () => onChange(isBottom ? 'right' : 'bottom')
    }}
/>
