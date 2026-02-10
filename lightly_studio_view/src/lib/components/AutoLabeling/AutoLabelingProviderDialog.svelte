<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { page } from '$app/state';
	import { Button } from '$lib/components/ui/button';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { LoaderCircle, CheckCircle, XCircle } from '@lucide/svelte';
	import { toast } from 'svelte-sonner';

	interface Props {
		providerMetadata: { provider_id: string; name: string; description: string } | null;
		isOpen: boolean;
		onOpenChange: (open: boolean) => void;
	}

	type ProviderParameter = {
		name: string;
		type: string;
		description: string;
		default: any;
		required: boolean;
	};

	let { providerMetadata, isOpen, onOpenChange }: Props = $props();

	let parameters = $state<Record<string, any>>({});
	let providerParameters = $state<ProviderParameter[]>([]);
	let isLoadingParameters = $state(false);
	let isSubmitting = $state(false);
	let jobId: string | null = $state(null);
	let jobStatus: 'pending' | 'running' | 'completed' | 'failed' | null = $state(null);
	let processedCount = $state(0);
	let jobError: string | null = $state(null);

	const collectionId = $derived(page.params.collection_id);

	// Load provider parameters when dialog opens
	$effect(() => {
		if (isOpen && providerMetadata && !jobId) {
			loadProviderParameters();
		}
	});

	async function loadProviderParameters() {
		if (!providerMetadata) return;

		isLoadingParameters = true;
		try {
			const response = await fetch(
				`/api/auto-labeling/providers/${providerMetadata.provider_id}/parameters`
			);
			if (!response.ok) throw new Error('Failed to load parameters');

			providerParameters = await response.json();

			// Initialize parameters with defaults
			const initialParams: Record<string, any> = {};
			for (const param of providerParameters) {
				if (param.default !== null && param.default !== undefined) {
					initialParams[param.name] = param.default;
				}
			}
			parameters = initialParams;
		} catch (error) {
			console.error('Failed to load provider parameters:', error);
			toast.error('Failed to load provider parameters');
		} finally {
			isLoadingParameters = false;
		}
	}

	let pollInterval: NodeJS.Timeout | null = null;

	async function pollJobStatus() {
		if (!jobId) return;

		try {
			const response = await fetch(`/api/auto-labeling/jobs/${jobId}`);
			const data = await response.json();

			jobStatus = data.status;
			processedCount = data.processed_count ?? 0;
			jobError = data.error_message;

			if (jobStatus === 'completed' || jobStatus === 'failed') {
				stopPolling();

				if (jobStatus === 'completed') {
					toast.success('Auto-labeling completed!', {
						description: `Processed ${processedCount} samples`
					});
				} else {
					toast.error('Auto-labeling failed', {
						description: jobError || 'Unknown error'
					});
				}
			}
		} catch (error) {
			console.error('Failed to poll job status:', error);
		}
	}

	function startPolling() {
		stopPolling();
		pollInterval = setInterval(pollJobStatus, 2000); // Poll every 2s
	}

	function stopPolling() {
		if (pollInterval) {
			clearInterval(pollInterval);
			pollInterval = null;
		}
	}

	onDestroy(() => {
		stopPolling();
	});

	async function handleSubmit() {
		if (!providerMetadata || !collectionId) return;

		isSubmitting = true;

		try {
			const response = await fetch(`/api/auto-labeling/collections/${collectionId}/jobs`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					provider_id: providerMetadata.provider_id,
					parameters: parameters
				})
			});

			if (!response.ok) throw new Error('Failed to start job');

			const data = await response.json();
			jobId = data.job_id;
			jobStatus = data.status;
			toast.success('Auto-labeling job started');
			startPolling();
		} catch (error) {
			toast.error('Failed to start job', {
				description: error instanceof Error ? error.message : String(error)
			});
		} finally {
			isSubmitting = false;
		}
	}
</script>

<Dialog.Root open={isOpen} {onOpenChange}>
	<Dialog.Portal>
		<Dialog.Overlay />
		<Dialog.Content class="max-h-[85vh] overflow-y-auto sm:max-w-md">
			<Dialog.Header>
				<Dialog.Title>{providerMetadata?.name || 'Auto-Labeling'}</Dialog.Title>
				<Dialog.Description>
					{providerMetadata?.description || 'Configure and run auto-labeling'}
				</Dialog.Description>
			</Dialog.Header>

			<div class="space-y-4">
				{#if jobStatus === 'running' || jobStatus === 'pending'}
					<div class="flex items-center gap-2 text-sm">
						<LoaderCircle class="size-4 animate-spin" />
						<span>Processing... ({processedCount} samples)</span>
					</div>
				{:else if jobStatus === 'completed'}
					<div class="flex items-center gap-2 text-sm text-emerald-600">
						<CheckCircle class="size-4" />
						<span>Completed! Processed {processedCount} samples.</span>
					</div>
				{:else if jobStatus === 'failed'}
					<div class="flex items-center gap-2 text-sm text-destructive">
						<XCircle class="size-4" />
						<span>Failed: {jobError}</span>
					</div>
				{:else if isLoadingParameters}
					<div class="flex items-center gap-2 text-sm text-muted-foreground">
						<LoaderCircle class="size-4 animate-spin" />
						<span>Loading parameters...</span>
					</div>
				{:else}
					<!-- Parameter form -->
					{#each providerParameters as param}
						<div class="space-y-2">
							<Label for={param.name}>
								{param.name}
								{#if param.required}
									<span class="text-destructive">*</span>
								{/if}
							</Label>
							{#if param.description}
								<p class="text-xs text-muted-foreground">{param.description}</p>
							{/if}

							{#if param.type === 'string' || param.type === 'tag_filter'}
								{#if param.name === 'api_key'}
									<Input
										id={param.name}
										type="password"
										placeholder={param.description}
										bind:value={parameters[param.name]}
									/>
								{:else}
									<Input
										id={param.name}
										type="text"
										placeholder={param.description}
										bind:value={parameters[param.name]}
									/>
								{/if}
							{:else if param.type === 'json'}
								<textarea
									id={param.name}
									placeholder={param.description}
									bind:value={parameters[param.name]}
									rows={3}
									class="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
								></textarea>
							{:else if param.type === 'int'}
								<Input
									id={param.name}
									type="number"
									step="1"
									placeholder={param.description}
									bind:value={parameters[param.name]}
								/>
							{:else if param.type === 'float'}
								<Input
									id={param.name}
									type="number"
									step="0.1"
									placeholder={param.description}
									bind:value={parameters[param.name]}
								/>
							{:else if param.type === 'bool'}
								<div class="flex items-center space-x-2">
									<input
										id={param.name}
										type="checkbox"
										bind:checked={parameters[param.name]}
										class="size-4"
									/>
									<Label for={param.name}>{param.description}</Label>
								</div>
							{:else}
								<Input
									id={param.name}
									type="text"
									placeholder={param.description}
									bind:value={parameters[param.name]}
								/>
							{/if}
						</div>
					{/each}
				{/if}
			</div>

			<Dialog.Footer>
				<Button variant="outline" onclick={() => onOpenChange(false)}>
					{jobStatus === 'completed' ? 'Close' : 'Cancel'}
				</Button>
				{#if !jobStatus || jobStatus === 'failed'}
					<Button onclick={handleSubmit} disabled={isSubmitting}>
						{isSubmitting ? 'Starting...' : 'Start Auto-Labeling'}
					</Button>
				{/if}
			</Dialog.Footer>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>
