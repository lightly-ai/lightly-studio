<script lang="ts">
    import * as Tabs from '$lib/components/ui/tabs';
    import type { SettingsDialogState } from '../settingsDialogState.svelte';
    import { AnnotationsTab } from '../AnnotationsTab';
    import { DisplayTab } from '../DisplayTab';
    import { ShortcutsTab } from '../ShortcutsTab';

    interface Props {
        value: string;
        dialogState: SettingsDialogState;
    }

    let { value = $bindable(), dialogState }: Props = $props();

    const tabs = [
        { value: 'shortcuts', label: 'Shortcuts', component: ShortcutsTab },
        { value: 'display', label: 'Display', component: DisplayTab },
        { value: 'annotations', label: 'Annotations', component: AnnotationsTab }
    ];
</script>

<Tabs.Root
    bind:value
    onValueChange={() => dialogState.clearRecording()}
    class="flex min-h-0 flex-1 flex-col"
>
    <Tabs.List
        class="mt-4 h-auto justify-start gap-6 rounded-none border-b border-border bg-transparent p-0 px-6"
    >
        {#each tabs as tab (tab.value)}
            <Tabs.Trigger
                value={tab.value}
                class="-mb-px rounded-none border-b-2 border-transparent px-0 pb-2.5 pt-0 text-muted-foreground hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none"
            >
                {tab.label}
            </Tabs.Trigger>
        {/each}
    </Tabs.List>
    {#each tabs as tab (tab.value)}
        <Tabs.Content value={tab.value} class="mt-0 min-h-0 flex-1 overflow-y-auto px-6 py-4">
            <tab.component {dialogState} />
        </Tabs.Content>
    {/each}
</Tabs.Root>
