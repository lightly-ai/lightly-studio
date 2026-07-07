<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import * as Dialog from '$lib/components/ui/dialog';
    import * as Tabs from '$lib/components/ui/tabs';
    import type { ClassSetConfig, ColorConfig } from './types';
    import ColoringControls from './ColoringControls/ColoringControls.svelte';
    import ManualClassSelector from './ManualClassSelector/ManualClassSelector.svelte';
    import TopNControls from './TopNControls/TopNControls.svelte';

    interface Props {
        /** Two-way bound flag controlling dialog visibility. */
        open: boolean;
        /** Every real class label available in the underlying matrix. Used to bound top-N and populate the manual selector. */
        allClasses: string[];
        /** The currently applied class-set selection. Copied into a draft each time the dialog opens. */
        config: ClassSetConfig;
        /** The currently applied coloring options. Copied into a draft each time the dialog opens. */
        color: ColorConfig;
        /** Invoked with the new config and color when the user clicks Apply. The dialog then closes itself. */
        onApply: (config: ClassSetConfig, color: ColorConfig) => void;
    }

    let { open = $bindable(), allClasses, config, color, onApply }: Props = $props();

    // Draft state, synced from the applied config every time the dialog opens.
    let draft: ClassSetConfig = $state({ ...config });
    let colorDraft: ColorConfig = $state({ ...color });
    $effect(() => {
        if (open) {
            draft = { ...config, manualClasses: [...config.manualClasses] };
            colorDraft = { ...color };
        }
    });

    // The number input can be cleared into a non-finite value; fall back to 1.
    const normalizedN = $derived(
        Number.isFinite(draft.n) ? Math.min(Math.max(draft.n, 1), allClasses.length) : 1
    );
    const canApply = $derived(
        draft.mode === 'topN' ? Number.isFinite(draft.n) : draft.manualClasses.length > 0
    );

    const apply = () => {
        onApply({ ...draft, n: normalizedN }, { ...colorDraft });
        open = false;
    };
</script>

<Dialog.Root bind:open>
    <Dialog.Content class="max-w-[420px]">
        <Dialog.Header>
            <Dialog.Title>Configure classes</Dialog.Title>
            <Dialog.Description>
                Choose which classes the confusion matrix shows.
            </Dialog.Description>
        </Dialog.Header>
        <Tabs.Root bind:value={draft.mode}>
            <Tabs.List class="grid w-full grid-cols-2">
                <Tabs.Trigger value="topN">Top N</Tabs.Trigger>
                <Tabs.Trigger value="manual">Manual</Tabs.Trigger>
            </Tabs.List>
            <Tabs.Content value="topN">
                <TopNControls
                    bind:n={draft.n}
                    bind:sortBy={draft.sortBy}
                    maxN={allClasses.length}
                />
            </Tabs.Content>
            <Tabs.Content value="manual">
                <ManualClassSelector bind:selected={draft.manualClasses} {allClasses} />
            </Tabs.Content>
        </Tabs.Root>
        <ColoringControls
            bind:intensity={colorDraft.intensity}
            bind:logScale={colorDraft.logScale}
        />
        <Dialog.Footer>
            <Button variant="ghost" onclick={() => (open = false)}>Cancel</Button>
            <Button onclick={apply} disabled={!canApply} data-testid="class-set-apply">
                Apply
            </Button>
        </Dialog.Footer>
    </Dialog.Content>
</Dialog.Root>
