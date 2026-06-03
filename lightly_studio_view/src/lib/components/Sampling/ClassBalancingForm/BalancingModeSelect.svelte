<script lang="ts">
    import { Label } from '$lib/components/ui/label';
    import * as Select from '$lib/components/ui/select';
    import {
        BALANCING_MODE_LABELS,
        type BalancingMode
    } from '$lib/components/Sampling/balancingMode';

    interface Props {
        balancingMode: BalancingMode;
        onBalancingModeChange: (mode: BalancingMode) => void;
    }

    let { balancingMode, onBalancingModeChange }: Props = $props();
</script>

<div class="grid grid-cols-4 items-center gap-4">
    <Label for="balancing-mode" class="text-right text-foreground">Balancing Mode</Label>
    <Select.Root
        type="single"
        name="balancing-mode"
        value={balancingMode}
        onValueChange={(value) => onBalancingModeChange(value as BalancingMode)}
    >
        <Select.Trigger
            id="balancing-mode"
            class="col-span-3"
            data-testid="sampling-dialog-balancing-mode-select"
        >
            {BALANCING_MODE_LABELS[balancingMode]}
        </Select.Trigger>
        <Select.Content>
            <Select.Group>
                <Select.Item
                    value="uniform"
                    label="Uniform"
                    data-testid="sampling-balancing-mode-uniform"
                >
                    Uniform
                </Select.Item>
                <Select.Item value="dictionary" label="Dictionary" disabled>
                    Dictionary (Coming soon)
                </Select.Item>
                <Select.Item
                    value="input"
                    label="Input"
                    data-testid="sampling-balancing-mode-input"
                    disabled
                >
                    Input (Coming soon)
                </Select.Item>
            </Select.Group>
        </Select.Content>
    </Select.Root>
</div>
