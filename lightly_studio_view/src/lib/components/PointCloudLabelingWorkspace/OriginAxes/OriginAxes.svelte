<script lang="ts">
    import { T } from '@threlte/core';

    /** Renders the X (red), Y (green) and Z (blue) axes at the scene origin. */
    interface Props {
        /** Length of each axis, in scene units (meters). */
        size?: number;
    }

    let { size = 3 }: Props = $props();
</script>

<T.AxesHelper args={[size]} />
