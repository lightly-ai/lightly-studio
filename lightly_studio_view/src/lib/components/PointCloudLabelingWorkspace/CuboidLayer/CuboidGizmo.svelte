<script lang="ts">
    import { useParentObject3D } from '@threlte/core';
    import { TransformControls } from '@threlte/extras';

    const parentObject3D = useParentObject3D();
</script>

<TransformControls
    enabled={false}
    mode="translate"
    space="local"
    size={0.75}
    autoPauseControls={false}
    object={parentObject3D.current}
/>
