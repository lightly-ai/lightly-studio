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
    <div
        class="flex h-7 shrink-0 items-center gap-2 rounded-md px-2 transition-colors hover:bg-accent"
    >
        <Checkbox
            id="select-all-checkbox"
            class="box-border size-3.5 rounded-[4px] border-[1.5px] [&>div]:size-full [&_svg]:size-2.5"
            {checked}
            onCheckedChange={handleCheckedChange}
            data-testid="select-all-button"
            aria-label={checked ? 'Deselect all' : 'Select all'}
        />
        {#if !compact}
            <Label
                for="select-all-checkbox"
                class="cursor-pointer text-[12.5px] font-normal text-diffuse-foreground hover:text-foreground"
            >
                Select all
            </Label>
        {/if}
    </div>
</Tooltip>
