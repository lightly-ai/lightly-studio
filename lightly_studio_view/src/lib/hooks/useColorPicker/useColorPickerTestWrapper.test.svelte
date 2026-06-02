<script lang="ts">
    import { useColorPicker } from './useColorPicker.svelte';

    let { label }: { label: string } = $props();

    const picker = useColorPicker(() => label);
</script>

<div data-testid="border-color">{picker.borderColor}</div>
<div data-testid="background-color">{picker.backgroundColor}</div>
<div data-testid="initial-color">{picker.initialColor}</div>
<div data-testid="initial-alpha">{picker.initialAlpha}</div>
<button data-testid="set-color" type="button" onclick={() => picker.setColor('#abcdef', 0.5)}
    >set</button
>
