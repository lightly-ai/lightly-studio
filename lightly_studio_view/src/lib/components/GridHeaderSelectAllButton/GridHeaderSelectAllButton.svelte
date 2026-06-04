<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Label } from '$lib/components/ui/label';

    interface Props {
        checked: boolean;
        onSelectAll: () => Promise<void>;
        onDeselectAll: () => void;
    }

    const { checked, onSelectAll, onDeselectAll }: Props = $props();

    const handleCheckedChange = (next: boolean) => {
        if (next) {
            void onSelectAll();
        } else {
            onDeselectAll();
        }
    };
</script>

<div class="flex h-8 shrink-0 items-center gap-2 px-2">
    <Checkbox
        id="select-all-checkbox"
        {checked}
        onCheckedChange={handleCheckedChange}
        data-testid="select-all-button"
        aria-label={checked ? 'Deselect all' : 'Select all'}
    />
    <Label
        for="select-all-checkbox"
        class="cursor-pointer text-sm font-normal text-diffuse-foreground hover:text-foreground"
    >
        Select all
    </Label>
</div>
