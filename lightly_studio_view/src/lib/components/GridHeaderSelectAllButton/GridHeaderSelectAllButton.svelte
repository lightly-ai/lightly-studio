<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Label } from '$lib/components/ui/label';
    import { Tooltip } from '$lib/components/ui/tooltip';

    interface Props {
        checked: boolean;
        onSelectAll: () => Promise<void>;
        onDeselectAll: () => void;
        compact?: boolean;
    }

    const { checked, onSelectAll, onDeselectAll, compact = false }: Props = $props();

    const handleCheckedChange = (next: boolean) => {
        if (next) {
            void onSelectAll();
        } else {
            onDeselectAll();
        }
    };

    const tooltipContent = $derived(
        checked
            ? 'Deselect all samples in the current view.'
            : 'Select all samples in the current view.'
    );
</script>

<Tooltip content={tooltipContent} position="top" triggerClass="inline-flex">
    <div class="flex h-8 shrink-0 items-center gap-2 px-2">
        <Checkbox
            id="select-all-checkbox"
            {checked}
            onCheckedChange={handleCheckedChange}
            data-testid="select-all-button"
            aria-label={checked ? 'Deselect all' : 'Select all'}
        />
        {#if !compact}
            <Label
                for="select-all-checkbox"
                class="cursor-pointer text-sm font-normal text-diffuse-foreground hover:text-foreground"
            >
                Select all
            </Label>
        {/if}
    </div>
</Tooltip>
