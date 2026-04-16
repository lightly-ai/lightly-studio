<script lang="ts">
  import MonacoEditor from '$lib/components/MonacoEditor.svelte';
  import type { editor } from 'monaco-editor';

  // Editor states
  let code = $state(`// Welcome to Monaco Editor Example
function fibonacci(n) {
  if (n <= 1) return n;
  return fibonacci(n - 1) + fibonacci(n - 2);
}

// Test the function
console.log('Fibonacci(10):', fibonacci(10));

// Example class
class Calculator {
  constructor() {
    this.result = 0;
  }

  add(value) {
    this.result += value;
    return this;
  }

  multiply(value) {
    this.result *= value;
    return this;
  }

  getResult() {
    return this.result;
  }
}

const calc = new Calculator();
calc.add(5).multiply(3).add(10);
console.log('Result:', calc.getResult());`);

  let pythonCode = $state(`# Python example
import math

def calculate_prime_factors(n):
    """Calculate prime factors of a number"""
    factors = []
    d = 2
    while d * d <= n:
        while (n % d) == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors

# Example usage
number = 315
print(f"Prime factors of {number}: {calculate_prime_factors(number)}")

# List comprehension example
squares = [x**2 for x in range(10) if x % 2 == 0]
print(f"Even squares: {squares}")`);

  let jsonCode = $state(`{
  "name": "Monaco Editor Example",
  "version": "1.0.0",
  "description": "A demonstration of Monaco Editor integration",
  "features": [
    "Syntax highlighting",
    "Auto-completion",
    "Error detection",
    "Multi-language support"
  ],
  "languages": {
    "javascript": true,
    "typescript": true,
    "python": true,
    "json": true,
    "html": true,
    "css": true
  },
  "configuration": {
    "theme": "vs-dark",
    "fontSize": 14,
    "lineNumbers": true,
    "minimap": true
  }
}`);

  let cssCode = $state(`/* CSS Example */
:root {
  --primary-color: #3498db;
  --secondary-color: #2ecc71;
  --background: #1a1a1a;
  --text-color: #ecf0f1;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.card {
  background: var(--background);
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}

.card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 12px rgba(0, 0, 0, 0.2);
}

@media (max-width: 768px) {
  .container {
    padding: 10px;
  }
}`);

  // Currently selected language and code
  let selectedLanguage = $state<'javascript' | 'python' | 'json' | 'css'>('javascript');
  let currentCode = $state(code);

  // Editor options
  let theme = $state<'vs' | 'vs-dark' | 'hc-black'>('vs-dark');
  let fontSize = $state(14);
  let minimap = $state(true);
  let wordWrap = $state<'off' | 'on'>('off');
  let lineNumbers = $state<'on' | 'off' | 'relative'>('on');
  let readOnly = $state(false);

  // Output from editor
  let editorOutput = $state('');
  let editorRef = $state<editor.IStandaloneCodeEditor | null>(null);

  // Handle language change
  function changeLanguage(lang: typeof selectedLanguage) {
    selectedLanguage = lang;
    switch (lang) {
      case 'javascript':
        currentCode = code;
        break;
      case 'python':
        currentCode = pythonCode;
        break;
      case 'json':
        currentCode = jsonCode;
        break;
      case 'css':
        currentCode = cssCode;
        break;
    }
  }

  // Handle code changes
  function handleCodeChange(value: string) {
    switch (selectedLanguage) {
      case 'javascript':
        code = value;
        break;
      case 'python':
        pythonCode = value;
        break;
      case 'json':
        jsonCode = value;
        break;
      case 'css':
        cssCode = value;
        break;
    }
    editorOutput = `Last change: ${new Date().toLocaleTimeString()}`;
  }

  // Handle editor mount
  function handleEditorMount(editor: editor.IStandaloneCodeEditor) {
    editorRef = editor;
    console.log('Editor mounted successfully');

    // Add custom keyboard shortcuts
    editor.addAction({
      id: 'custom-save',
      label: 'Save',
      keybindings: [2048 /* CtrlCmd */ | 83 /* KeyS */],
      run: () => {
        editorOutput = 'Save action triggered (Cmd/Ctrl+S)';
        return null;
      }
    });
  }

  // Format code
  function formatCode() {
    if (editorRef) {
      editorRef.getAction('editor.action.formatDocument')?.run();
      editorOutput = 'Code formatted';
    }
  }

  // Clear editor
  function clearEditor() {
    currentCode = '';
    handleCodeChange('');
    editorOutput = 'Editor cleared';
  }

  // Copy code to clipboard
  async function copyCode() {
    try {
      await navigator.clipboard.writeText(currentCode);
      editorOutput = 'Code copied to clipboard';
    } catch (err) {
      editorOutput = 'Failed to copy code';
    }
  }
</script>

<div class="editor-page">
  <header class="editor-header">
    <h1>Monaco Editor Example</h1>
    <p>A feature-rich code editor powered by Monaco Editor (the engine behind VS Code)</p>
  </header>

  <div class="controls-section">
    <!-- Language Selection -->
    <div class="control-group">
      <label>Language:</label>
      <div class="button-group">
        <button
          class:active={selectedLanguage === 'javascript'}
          on:click={() => changeLanguage('javascript')}
        >
          JavaScript
        </button>
        <button
          class:active={selectedLanguage === 'python'}
          on:click={() => changeLanguage('python')}
        >
          Python
        </button>
        <button
          class:active={selectedLanguage === 'json'}
          on:click={() => changeLanguage('json')}
        >
          JSON
        </button>
        <button
          class:active={selectedLanguage === 'css'}
          on:click={() => changeLanguage('css')}
        >
          CSS
        </button>
      </div>
    </div>

    <!-- Theme Selection -->
    <div class="control-group">
      <label>Theme:</label>
      <select bind:value={theme}>
        <option value="vs">Light</option>
        <option value="vs-dark">Dark</option>
        <option value="hc-black">High Contrast</option>
      </select>
    </div>

    <!-- Font Size -->
    <div class="control-group">
      <label>Font Size:</label>
      <input
        type="range"
        min="10"
        max="24"
        bind:value={fontSize}
      />
      <span>{fontSize}px</span>
    </div>

    <!-- Options -->
    <div class="control-group">
      <label>
        <input type="checkbox" bind:checked={minimap} />
        Minimap
      </label>
      <label>
        <input type="checkbox" bind:checked={readOnly} />
        Read Only
      </label>
      <label>
        <input
          type="checkbox"
          checked={wordWrap === 'on'}
          on:change={(e) => wordWrap = e.currentTarget.checked ? 'on' : 'off'}
        />
        Word Wrap
      </label>
    </div>

    <!-- Line Numbers -->
    <div class="control-group">
      <label>Line Numbers:</label>
      <select bind:value={lineNumbers}>
        <option value="on">On</option>
        <option value="off">Off</option>
        <option value="relative">Relative</option>
      </select>
    </div>

    <!-- Actions -->
    <div class="control-group">
      <button class="action-button" on:click={formatCode}>
        Format Code
      </button>
      <button class="action-button" on:click={copyCode}>
        Copy Code
      </button>
      <button class="action-button danger" on:click={clearEditor}>
        Clear
      </button>
    </div>
  </div>

  <!-- Monaco Editor -->
  <div class="editor-container">
    <MonacoEditor
      bind:value={currentCode}
      language={selectedLanguage}
      {theme}
      {fontSize}
      {minimap}
      {wordWrap}
      {lineNumbers}
      {readOnly}
      onChange={handleCodeChange}
      onEditorMount={handleEditorMount}
      height="500px"
    />
  </div>

  <!-- Output -->
  {#if editorOutput}
    <div class="output-section">
      <strong>Status:</strong> {editorOutput}
    </div>
  {/if}

  <!-- Features Section -->
  <div class="features-section">
    <h2>Features</h2>
    <ul>
      <li>Syntax highlighting for multiple languages</li>
      <li>IntelliSense and auto-completion</li>
      <li>Error detection and linting</li>
      <li>Code formatting</li>
      <li>Multiple themes (Light, Dark, High Contrast)</li>
      <li>Minimap navigation</li>
      <li>Customizable font size</li>
      <li>Word wrap support</li>
      <li>Line number options (on/off/relative)</li>
      <li>Read-only mode</li>
      <li>Custom keyboard shortcuts (Try Cmd/Ctrl+S)</li>
    </ul>
  </div>
</div>

<style>
  .editor-page {
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;
  }

  .editor-header {
    margin-bottom: 2rem;
  }

  .editor-header h1 {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    color: var(--text-color, #333);
  }

  .editor-header p {
    color: var(--text-secondary, #666);
  }

  .controls-section {
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem;
    margin-bottom: 1.5rem;
    padding: 1rem;
    background: var(--background-secondary, #f5f5f5);
    border-radius: 8px;
  }

  .control-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .control-group label {
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .button-group {
    display: flex;
    gap: 0.25rem;
  }

  .button-group button {
    padding: 0.25rem 0.75rem;
    border: 1px solid var(--border-color, #ddd);
    background: white;
    cursor: pointer;
    transition: all 0.2s;
  }

  .button-group button:first-child {
    border-radius: 4px 0 0 4px;
  }

  .button-group button:last-child {
    border-radius: 0 4px 4px 0;
  }

  .button-group button.active {
    background: var(--primary-color, #3498db);
    color: white;
    border-color: var(--primary-color, #3498db);
  }

  select {
    padding: 0.25rem 0.5rem;
    border: 1px solid var(--border-color, #ddd);
    border-radius: 4px;
    background: white;
  }

  input[type="range"] {
    width: 100px;
  }

  input[type="checkbox"] {
    cursor: pointer;
  }

  .action-button {
    padding: 0.375rem 1rem;
    border: 1px solid var(--border-color, #ddd);
    background: white;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
    font-weight: 500;
  }

  .action-button:hover {
    background: var(--primary-color, #3498db);
    color: white;
    border-color: var(--primary-color, #3498db);
  }

  .action-button.danger:hover {
    background: #e74c3c;
    border-color: #e74c3c;
  }

  .editor-container {
    margin-bottom: 1.5rem;
  }

  .output-section {
    padding: 1rem;
    background: #e8f5e9;
    border-radius: 4px;
    margin-bottom: 1.5rem;
    color: #2e7d32;
  }

  .features-section {
    padding: 1.5rem;
    background: var(--background-secondary, #f5f5f5);
    border-radius: 8px;
  }

  .features-section h2 {
    margin-bottom: 1rem;
    color: var(--text-color, #333);
  }

  .features-section ul {
    list-style: disc;
    padding-left: 1.5rem;
    color: var(--text-secondary, #666);
  }

  .features-section li {
    margin-bottom: 0.5rem;
  }

  /* Dark mode support */
  @media (prefers-color-scheme: dark) {
    .controls-section,
    .features-section {
      background: #2d2d2d;
    }

    .button-group button,
    select,
    .action-button {
      background: #3d3d3d;
      color: #fff;
      border-color: #4d4d4d;
    }

    .output-section {
      background: #1b5e20;
      color: #a5d6a7;
    }
  }
</style>