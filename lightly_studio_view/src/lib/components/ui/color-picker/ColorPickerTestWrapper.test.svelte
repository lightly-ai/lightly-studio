<script lang="ts">
    import ColorPicker from './color-picker.svelte';

    let latestColor = $state('');

    function handleChange(color: string, alpha: number) {
        latestColor = `${color}:${alpha}`;
    }
</script>

<ColorPicker onChange={handleChange}>
    <span>Open color picker</span>
</ColorPicker>

<span data-testid="latest-color">{latestColor}</span>
