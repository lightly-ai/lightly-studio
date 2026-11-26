<script lang="ts">
    import { Pane, PaneGroup } from 'paneforge';
    import { useCollapsiblePane } from './useCollapsiblePane.svelte';

    let { storageKey }: { storageKey: string } = $props();
    // svelte-ignore state_referenced_locally
    const pane = useCollapsiblePane(storageKey);
</script>

<button type="button" onclick={pane.toggle}>Toggle</button>
<span data-testid="collapsed">{pane.collapsed}</span>
<PaneGroup direction="horizontal">
    <Pane defaultSize={72}>Main</Pane>
    <Pane
        bind:this={pane.pane}
        defaultSize={28}
        minSize={20}
        collapsedSize={0}
        collapsible
        onCollapse={() => pane.setCollapsed(true)}
        onExpand={() => pane.setCollapsed(false)}
    >
        Details
    </Pane>
</PaneGroup>
