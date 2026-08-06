<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { Label } from '$lib/components/ui/label';

    interface ColorByRepeatGroupCheckboxProps {
        checked: boolean;
        onCheckedChange: (checked: boolean) => void;
    }

    const { checked, onCheckedChange }: ColorByRepeatGroupCheckboxProps = $props();
</script>

<div
    class="flex items-center gap-2"
    data-testid="color-by-repeat-group-checkbox"
>
    <Checkbox
        id="color-by-repeat-group"
        {checked}
        onCheckedChange={(value: boolean | 'indeterminate') => onCheckedChange(value === true)}
        data-testid="color-by-repeat-group-input"
    />
    <Label
        for="color-by-repeat-group"
        class="cursor-pointer text-xs font-normal text-muted-foreground"
    >
        Color by repeat group
    </Label>
</div>
