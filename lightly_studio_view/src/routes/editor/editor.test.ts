import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, waitFor } from '@testing-library/svelte';
import EditorPage from './+page.svelte';

// Mock the Monaco loader
vi.mock('@monaco-editor/loader', () => ({
  default: {
    init: vi.fn().mockResolvedValue({
      editor: {
        create: vi.fn().mockReturnValue({
          getValue: vi.fn().mockReturnValue(''),
          setValue: vi.fn(),
          updateOptions: vi.fn(),
          getModel: vi.fn().mockReturnValue(null),
          onDidChangeModelContent: vi.fn(),
          addAction: vi.fn(),
          getAction: vi.fn(),
          dispose: vi.fn()
        }),
        setModelLanguage: vi.fn()
      }
    })
  }
}));

describe('Editor Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render the editor page', () => {
    const { getByText } = render(EditorPage);
    expect(getByText('Monaco Editor Example')).toBeTruthy();
  });

  it('should display language options', () => {
    const { getByText } = render(EditorPage);
    expect(getByText('JavaScript')).toBeTruthy();
    expect(getByText('Python')).toBeTruthy();
    expect(getByText('JSON')).toBeTruthy();
    expect(getByText('CSS')).toBeTruthy();
  });

  it('should display theme options', () => {
    const { container } = render(EditorPage);
    const themeSelect = container.querySelector('select');
    expect(themeSelect).toBeTruthy();

    const options = themeSelect?.querySelectorAll('option');
    expect(options?.length).toBe(3);
  });

  it('should display editor controls', () => {
    const { getByText } = render(EditorPage);
    expect(getByText('Format Code')).toBeTruthy();
    expect(getByText('Copy Code')).toBeTruthy();
    expect(getByText('Clear')).toBeTruthy();
  });

  it('should display features section', () => {
    const { getByText } = render(EditorPage);
    expect(getByText('Features')).toBeTruthy();
    expect(getByText('Syntax highlighting for multiple languages')).toBeTruthy();
  });
});