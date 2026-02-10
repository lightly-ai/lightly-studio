<script lang="ts">
	import { onMount } from 'svelte';
	import * as Dialog from '$lib/components/ui/dialog';
	import { LoaderCircle, AlertCircle, ChevronRight } from '@lucide/svelte';
	import { useAutoLabelingDialog } from '$lib/hooks/useAutoLabelingDialog/useAutoLabelingDialog';
	import AutoLabelingProviderDialog from './AutoLabelingProviderDialog.svelte';

	type ProviderMetadata = {
		provider_id: string;
		name: string;
		description: string;
	};

	let providers: ProviderMetadata[] = $state([]);
	let isLoading = $state(true);
	let errorMessage: string | null = $state(null);
	let selectedProvider: ProviderMetadata | null = $state(null);
	let isProviderDialogOpen = $state(false);

	const { isAutoLabelingDialogOpen, openAutoLabelingDialog, closeAutoLabelingDialog } =
		useAutoLabelingDialog();

	const loadProviders = async () => {
		isLoading = true;
		errorMessage = null;
		try {
			const response = await fetch('/api/auto-labeling/providers');
			if (!response.ok) throw new Error('Failed to load providers');
			providers = await response.json();
		} catch (error) {
			errorMessage = error instanceof Error ? error.message : 'Failed to load providers';
		} finally {
			isLoading = false;
		}
	};

	onMount(() => {
		loadProviders();
	});

	const handleProviderClick = (provider: ProviderMetadata) => {
		selectedProvider = provider;
		closeAutoLabelingDialog();
		isProviderDialogOpen = true;
	};
</script>

<Dialog.Root
	open={$isAutoLabelingDialogOpen}
	onOpenChange={(open) => (open ? openAutoLabelingDialog() : closeAutoLabelingDialog())}
>
	<Dialog.Portal>
		<Dialog.Overlay />
		<Dialog.Content class="flex max-h-[80vh] w-[90vw] flex-col overflow-hidden sm:w-[520px]">
			<div class="flex items-start justify-between border-b px-4 py-3 pr-12">
				<div>
					<h3 class="text-base font-semibold">Auto-Labeling</h3>
					<p class="text-sm text-muted-foreground">
						Select a provider to auto-label your data.
					</p>
				</div>
				<span
					class="inline-flex items-center rounded-full bg-secondary px-2 py-1 text-xs font-medium text-secondary-foreground"
				>
					{providers.length}
				</span>
			</div>

			<div class="max-h-[65vh] flex-1 overflow-y-auto">
				{#if isLoading}
					<div class="flex items-center gap-2 p-4 text-sm text-muted-foreground">
						<LoaderCircle class="size-4 animate-spin" />
						<span>Loading providers…</span>
					</div>
				{:else if errorMessage}
					<div class="flex items-center gap-2 p-4 text-sm text-destructive">
						<AlertCircle class="size-4" />
						<span>{errorMessage}</span>
					</div>
				{:else}
					<ul class="divide-y divide-border">
						{#each providers as provider}
							<li>
								<button
									type="button"
									class="flex w-full items-center justify-between p-3 text-left hover:bg-muted"
									onclick={() => handleProviderClick(provider)}
								>
									<div class="flex flex-col gap-1">
										<span class="font-medium">{provider.name}</span>
										<span class="text-xs text-muted-foreground">{provider.description}</span>
									</div>
									<ChevronRight class="size-4 text-muted-foreground" />
								</button>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<AutoLabelingProviderDialog
	providerMetadata={selectedProvider}
	isOpen={isProviderDialogOpen}
	onOpenChange={(open) => {
		isProviderDialogOpen = open;
		if (!open) selectedProvider = null;
	}}
/>
