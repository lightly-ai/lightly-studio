<script lang="ts">
    import { Slider as SliderPrimitive } from 'bits-ui';

    let { hue, onHueChange }: { hue: number; onHueChange: (hue: number) => void } = $props();
</script>

<SliderPrimitive.Root
    type="single"
    min={0}
    max={360}
    step={1}
    value={hue}
    onValueChange={onHueChange}
    class="relative flex h-4 w-full touch-none select-none items-center"
>
    <span
        class="relative h-4 w-full grow rounded"
        style="background: linear-gradient(to right, #f00, #ff0, #0f0, #0ff, #00f, #f0f, #f00)"
    ></span>
    <SliderPrimitive.Thumb
        index={0}
        aria-label="Hue"
        class="focus-visible:ring-ring block h-4 w-1 rounded-none border-x border-white shadow-sm focus-visible:outline-none focus-visible:ring-2"
    />
</SliderPrimitive.Root>
