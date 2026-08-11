<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import {
        BLUR_SCORE_KEY,
        LIGHTING_SCORE_KEY,
        MOTION_SCORE_KEY,
        SHAKE_SCORE_KEY
    } from '$lib/constants';
    import {
        BLUR_SCORE_LOW_MAX,
        LIGHTING_SCORE_LOW_MAX,
        MOTION_SCORE_LOW_MAX,
        SHAKE_SCORE_HIGH_MIN
    } from '$lib/utils';

    const { metadataInfo } = useMetadataFilters();
    const { filterParams, setBlurry, setPoorLighting, setStaticCamera, setShaky } =
        useVideoFilters();

    const hasBlurScore = $derived(($metadataInfo ?? []).some((info) => info.name === BLUR_SCORE_KEY));
    const hasLightingScore = $derived(
        ($metadataInfo ?? []).some((info) => info.name === LIGHTING_SCORE_KEY)
    );
    const hasMotionScore = $derived(
        ($metadataInfo ?? []).some((info) => info.name === MOTION_SCORE_KEY)
    );
    const hasShakeScore = $derived(
        ($metadataInfo ?? []).some((info) => info.name === SHAKE_SCORE_KEY)
    );

    const isBlurryActive = $derived(!!$filterParams?.filters?.blurry);
    const isPoorLightingActive = $derived(!!$filterParams?.filters?.poor_lighting);
    const isStaticCameraActive = $derived(!!$filterParams?.filters?.static_camera);
    const isShakyActive = $derived(!!$filterParams?.filters?.shaky);
</script>

{#if hasBlurScore}
    <Button
        type="button"
        size="sm"
        variant={isBlurryActive ? 'default' : 'outline'}
        class="h-7 px-2.5 text-xs"
        onclick={() => setBlurry(!isBlurryActive)}
        aria-pressed={isBlurryActive}
        data-testid="blurry-filter"
        title={`Show videos whose blur_score is below ${BLUR_SCORE_LOW_MAX}`}
    >
        Blurry
    </Button>
{/if}

{#if hasLightingScore}
    <Button
        type="button"
        size="sm"
        variant={isPoorLightingActive ? 'default' : 'outline'}
        class="h-7 px-2.5 text-xs"
        onclick={() => setPoorLighting(!isPoorLightingActive)}
        aria-pressed={isPoorLightingActive}
        data-testid="poor-lighting-filter"
        title={`Show videos whose lighting_score is below ${LIGHTING_SCORE_LOW_MAX}`}
    >
        Poor lighting
    </Button>
{/if}

{#if hasMotionScore}
    <Button
        type="button"
        size="sm"
        variant={isStaticCameraActive ? 'default' : 'outline'}
        class="h-7 px-2.5 text-xs"
        onclick={() => setStaticCamera(!isStaticCameraActive)}
        aria-pressed={isStaticCameraActive}
        data-testid="static-camera-filter"
        title={`Show videos whose motion_score is below ${MOTION_SCORE_LOW_MAX}`}
    >
        Static camera
    </Button>
{/if}

{#if hasShakeScore}
    <Button
        type="button"
        size="sm"
        variant={isShakyActive ? 'default' : 'outline'}
        class="h-7 px-2.5 text-xs"
        onclick={() => setShaky(!isShakyActive)}
        aria-pressed={isShakyActive}
        data-testid="shaky-filter"
        title={`Show videos whose shake_score is above ${SHAKE_SCORE_HIGH_MIN}`}
    >
        Shaky
    </Button>
{/if}
