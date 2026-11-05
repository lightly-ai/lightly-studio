<script lang="ts">
    import { useClassColorPicker, useSourceColorPicker } from './useColorPicker.svelte';

    let { label, kind = 'class' }: { label: string; kind?: 'class' | 'source' } = $props();

    // The kind is fixed per test, so reading it once is intended.
    // svelte-ignore state_referenced_locally
    const usePicker = kind === 'source' ? useSourceColorPicker : useClassColorPicker;
    const picker = usePicker(() => label);
</script>

<div data-testid="border-color">{picker.borderColor}</div>
<div data-testid="background-color">{picker.backgroundColor}</div>
<div data-testid="initial-color">{picker.initialColor}</div>
<div data-testid="initial-alpha">{picker.initialAlpha}</div>
<button
    data-testid="set-default"
    type="button"
    onclick={() => picker.setColor(picker.defaultColor, 1)}>set default</button
>
<button data-testid="set-color" type="button" onclick={() => picker.setColor('#abcdef', 0.5)}
    >set</button
>
<button data-testid="cancel" type="button" onclick={() => picker.finishColorChange(false)}
    >cancel</button
>
<button data-testid="apply" type="button" onclick={() => picker.finishColorChange(true)}
    >apply</button
>
