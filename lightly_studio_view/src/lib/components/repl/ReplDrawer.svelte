<script lang="ts">
    import CodeEditor from './CodeEditor.svelte';
    import ReplOutput from './ReplOutput.svelte';
    import { onMount } from 'svelte';

    let isOpen = false;
    let code = `
# List all indexed datasets
datasets = dataset_resolver.get_all(session=session)
print(f"Found {len(datasets)} dataset(s):")
for ds in datasets:
    print(f"  - {ds.name} (ID: {ds.dataset_id})")
`;
    let logs: { type: string; text: string }[] = [];
    let ws: WebSocket;
    let isRunning = false;

    function toggle() {
        isOpen = !isOpen;
    }

    function connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host; 
        // TODO(Gemini, 12/2025): Handle dev mode proxy port if needed.
        const url = `${protocol}//${host}/api/repl/ws`;
        
        console.log('Connecting to REPL:', url);
        ws = new WebSocket(url);
        
        ws.onopen = () => {
            logs = [...logs, { type: 'stream', text: 'Connected to REPL kernel.\n' }];
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'done') {
                isRunning = false;
            } else if (data.type === 'stream') {
                logs = [...logs, { type: 'stream', text: data.text }];
            } else if (data.type === 'result') {
                logs = [...logs, { type: 'result', text: data.data + '\n' }];
            } else if (data.type === 'error') {
                logs = [...logs, { type: 'error', text: `${data.ename}: ${data.evalue}\n${data.traceback.join('\n')}\n` }];
            }
        };
        
        ws.onclose = () => {
            logs = [...logs, { type: 'stream', text: 'Connection closed.\n' }];
        };
        
        ws.onerror = (err) => {
             console.error('WebSocket error:', err);
             logs = [...logs, { type: 'error', text: 'WebSocket connection error.\n' }];
        };
    }

    onMount(() => {
        // Delay connection slightly to ensure page is loaded
        setTimeout(connect, 1000);
        return () => {
            if (ws) ws.close();
        };
    });

    function runCode() {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            logs = [...logs, { type: 'error', text: 'WebSocket not connected. Reconnecting...\n' }];
            connect();
            return;
        }
        isRunning = true;
        logs = [...logs, { type: 'stream', text: '> Running code...\n' }];
        ws.send(JSON.stringify({ code }));
    }
</script>

<div class="fixed bottom-0 left-0 right-0 z-50 flex flex-col bg-gray-900 text-white shadow-lg transition-all duration-300"
     style="height: {isOpen ? '400px' : '40px'}">
    
    <!-- Header -->
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <!-- svelte-ignore a11y-no-static-element-interactions -->
    <div class="flex h-10 items-center justify-between bg-gray-800 px-4 cursor-pointer border-t border-gray-700" on:click={toggle}>
        <div class="flex items-center gap-2">
            <span class="font-bold text-sm">Lightly Studio REPL</span>
            <span class="text-xs text-gray-400">{isOpen ? '(Click to collapse)' : '(Click to expand)'}</span>
        </div>
        <div class="flex items-center gap-2">
            <button class="rounded bg-blue-600 px-3 py-1 text-xs font-semibold hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed" 
                    on:click|stopPropagation={runCode} disabled={isRunning}>
                {isRunning ? 'Running...' : 'Run (Shift+Enter)'}
            </button>
        </div>
    </div>

    <!-- Content -->
    {#if isOpen}
        <div class="flex h-full flex-row overflow-hidden">
            <div class="w-1/2 border-r border-gray-700 relative">
                <CodeEditor bind:value={code} on:run={runCode} />
            </div>
            <div class="w-1/2 bg-black">
                <ReplOutput {logs} />
            </div>
        </div>
    {/if}
</div>
