<script lang="ts">
    import { Select, type SelectItem } from '$lib/components/Select';
    import { useClassifiersMenu } from '$lib/hooks/useClassifiers/useClassifiersMenu';
    import { useSamplingDialog } from '$lib/hooks/useSamplingDialog/useSamplingDialog';
    import { useExportDialog } from '$lib/hooks/useExportDialog/useExportDialog';
    import { useSettingsDialog } from '$lib/hooks/useSettingsDialog/useSettingsDialog';
    import { useOperatorsDialog } from '$lib/hooks/useOperatorsDialog/useOperatorsDialog';
    import {
        Puzzle as PuzzleIcon,
        Download as DownloadIcon,
        Settings as SettingsIcon,
        BrainCircuit as BrainCircuitIcon,
        WandSparkles as WandSparklesIcon
    } from '@lucide/svelte';

    import type { CollectionView } from '$lib/api/lightly_studio_local';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';
    import type { LightlyEnterpriseSession } from '$lib/hooks/useAuth/getLightlyEnterpriseSession/getLightlyEnterpriseSession';

    let {
        isImages = false,
        isVideos = false,
        hasEmbeddings = false,
        collection,
        user
    } = $props<{
        isImages?: boolean;
        isVideos?: boolean;
        hasEmbeddings?: boolean;
        collection: CollectionView;
        user?: LightlyEnterpriseSession['user'];
    }>();

    const { openClassifiersMenu } = useClassifiersMenu();
    const { openSamplingDialog } = useSamplingDialog();
    const { openExportDialog } = useExportDialog();
    const { openSettingsDialog } = useSettingsDialog();
    const { openOperatorsDialog } = useOperatorsDialog();

    type MenuAction = SelectItem & { onSelect: () => void };

    const hasClassifier = $derived(isImages && hasEmbeddings);
    const hasSampling = $derived(isImages || isVideos);
    const hasExport = $derived(
        collection.sample_type == 'image' ||
            collection.sample_type == 'video' ||
            collection.sample_type == 'video_frame'
    );

    const isEditor = $derived(hasMinimumRole(user?.role, 'editor'));

    const menuActions = $derived.by<MenuAction[]>(() => {
        const items: MenuAction[] = [];

        if (hasClassifier && isEditor) {
            items.push({
                value: 'menu-classifiers',
                label: 'Few Shot Classifier',
                icon: BrainCircuitIcon,
                testId: 'menu-classifiers',
                onSelect: openClassifiersMenu
            });
        }

        if (hasSampling && isEditor) {
            items.push({
                value: 'menu-sampling',
                label: 'Sampling',
                icon: WandSparklesIcon,
                testId: 'menu-sampling',
                onSelect: openSamplingDialog
            });
        }

        if (isEditor) {
            items.push({
                value: 'menu-operators',
                label: 'Plugins',
                icon: PuzzleIcon,
                testId: 'menu-operators',
                onSelect: openOperatorsDialog
            });
        }

        if (hasExport) {
            items.push({
                value: 'menu-export',
                label: 'Export',
                icon: DownloadIcon,
                testId: 'menu-export',
                onSelect: openExportDialog
            });
        }

        if (isEditor) {
            items.push({
                value: 'menu-settings',
                label: 'Settings',
                icon: SettingsIcon,
                testId: 'menu-settings',
                onSelect: openSettingsDialog
            });
        }

        return items;
    });

    let selectedValue = $state<string | undefined>(undefined);

    const handleValueChange = (value: string) => {
        const action = menuActions.find((item) => item.value === value);
        selectedValue = undefined;
        action?.onSelect();
    };
</script>

{#if menuActions.length > 0}
    <Select
        bind:value={selectedValue}
        triggerLabel="Menu"
        items={menuActions}
        hideSelectionMarker
        itemsAsLinks
        onValueChange={handleValueChange}
        variant="ghost"
        class="nav-button w-[100px]"
        testId="menu-trigger"
    />
{/if}
