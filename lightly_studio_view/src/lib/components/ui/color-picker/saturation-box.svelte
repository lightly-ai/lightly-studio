<script lang="ts">
    import { hexToHsl, hslToHex } from './color-picker.helpers';

    type Hsl = ReturnType<typeof hexToHsl>;

    interface Props {
        hsl: Hsl;
        onPick: (saturation: number, lightness: number) => void;
    }

    let { hsl, onPick }: Props = $props();

    let isDragging = false;

    const arrowSteps: Record<string, [number, number]> = {
        ArrowLeft: [-1, 0],
        ArrowRight: [1, 0],
        ArrowUp: [0, 1],
        ArrowDown: [0, -1]
    };

    function clamp(value: number): number {
        return Math.max(0, Math.min(100, value));
    }

    function pickFromPointer(e: PointerEvent): void {
        const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;
        const y = (e.clientY - rect.top) / rect.height;
        onPick(clamp(Math.round(x * 100)), clamp(Math.round((1 - y) * 100)));
    }

    function handlePointerDown(e: PointerEvent): void {
        (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
        isDragging = true;
        pickFromPointer(e);
    }

    function handlePointerMove(e: PointerEvent): void {
        if (isDragging) pickFromPointer(e);
    }

    function handleKeyDown(e: KeyboardEvent): void {
        const step = arrowSteps[e.key];
        if (!step) return;
        e.preventDefault();
        const size = e.shiftKey ? 10 : 1;
        onPick(clamp(hsl.s + step[0] * size), clamp(hsl.l + step[1] * size));
    }
</script>

<div
    class="relative h-28 cursor-crosshair touch-none rounded"
    style={`background-image: linear-gradient(to top, #000, transparent), linear-gradient(to right, #fff, hsl(${hsl.h}, 100%, 50%))`}
    role="slider"
    aria-label="Saturation and lightness"
    aria-valuetext={`Saturation ${hsl.s}%, lightness ${hsl.l}%`}
    aria-valuenow={hsl.s}
    tabindex="0"
    onpointerdown={handlePointerDown}
    onpointermove={handlePointerMove}
    onpointerup={() => (isDragging = false)}
    onpointercancel={() => (isDragging = false)}
    onkeydown={handleKeyDown}
>
    <!-- Selection indicator -->
    <div
        class="absolute h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow-md"
        style={`left: ${hsl.s}%; top: ${100 - hsl.l}%; background-color: ${hslToHex(hsl)}`}
    ></div>
</div>
