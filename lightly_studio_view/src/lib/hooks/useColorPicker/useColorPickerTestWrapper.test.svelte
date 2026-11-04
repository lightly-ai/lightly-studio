<script lang="ts">
    import { useClassColorPicker, useSourceColorPicker } from './useColorPicker.svelte';

    import type { CustomColor } from '$lib/hooks/useCustomLabelColors';

    let {
        label,
        kind = 'class',
        onCommit
    }: {
        label: string;
        kind?: 'class' | 'source';
        onCommit?: (color: CustomColor) => Promise<void>;
    } = $props();

    // The kind is fixed per test, so reading it once is intended.
    // svelte-ignore state_referenced_locally
    const picker =
        kind === 'source'
            ? useSourceColorPicker(() => label)
            : useClassColorPicker(() => label, { onCommit });
</script>

<div data-testid="border-color">{picker.borderColor}</div>
<div data-testid="background-color">{picker.backgroundColor}</div>
<div data-testid="initial-color">{picker.initialColor}</div>
<div data-testid="initial-alpha">{picker.initialAlpha}</div>
<button data-testid="set-color" type="button" onclick={() => picker.setColor('#abcdef', 0.5)}
    >set</button
>
<button data-testid="set-other-color" type="button" onclick={() => picker.setColor('#bbbbbb', 1)}
    >set other</button
>
<button data-testid="cancel" type="button" onclick={() => picker.finishColorChange(false)}
    >cancel</button
>
<button data-testid="apply" type="button" onclick={() => picker.finishColorChange(true)}
    >apply</button
>
