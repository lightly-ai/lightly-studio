<script lang="ts" module>
    import DOMPurify from 'dompurify';
    import { Marked } from 'marked';

    const markdown = new Marked({
        renderer: {
            html: ({ text }) =>
                text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
        }
    });

    const ALLOWED_TAGS = [
        'a',
        'blockquote',
        'br',
        'code',
        'del',
        'em',
        'h1',
        'h2',
        'h3',
        'h4',
        'h5',
        'h6',
        'hr',
        'li',
        'ol',
        'p',
        'pre',
        'strong',
        'table',
        'tbody',
        'td',
        'th',
        'thead',
        'tr',
        'ul'
    ];

    function toSafeFragment(text: string): DocumentFragment {
        const fragment = DOMPurify.sanitize(markdown.parse(text, { async: false }), {
            ALLOWED_TAGS,
            ALLOWED_ATTR: ['href', 'start', 'title'],
            ALLOWED_URI_REGEXP: /^https?:\/\//i,
            RETURN_DOM_FRAGMENT: true
        });
        // A link in the same tab would leave the dataset and stop a running reply.
        for (const link of fragment.querySelectorAll('a[href]')) {
            link.setAttribute('target', '_blank');
            link.setAttribute('rel', 'noopener noreferrer');
        }
        return fragment;
    }
</script>

<script lang="ts">
    interface Props {
        text: string;
        /** The text grows while the agent writes. It renders at most once per frame. */
        isStreaming?: boolean;
    }

    const { text, isStreaming = false }: Props = $props();
    let latestText = '';
    let pendingFrame: number | undefined;

    function renderMarkdown(element: HTMLElement) {
        latestText = text;
        if (!isStreaming) {
            element.replaceChildren(toSafeFragment(latestText));
            return;
        }
        // Keep the pending frame: canceling it on each new piece of text would delay every
        // render until the agent pauses.
        pendingFrame ??= requestAnimationFrame(() => {
            pendingFrame = undefined;
            element.replaceChildren(toSafeFragment(latestText));
        });
    }
</script>

<div
    class="min-w-0 break-words text-sm leading-relaxed [&_a]:text-primary [&_a]:underline [&_blockquote]:border-l-2 [&_blockquote]:pl-3 [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_h1]:font-semibold [&_h2]:font-semibold [&_h3]:font-semibold [&_li+li]:mt-1 [&_ol]:list-decimal [&_ol]:pl-5 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-muted [&_pre]:p-3 [&_table]:block [&_table]:overflow-x-auto [&_td]:px-2 [&_th]:px-2 [&_ul]:list-disc [&_ul]:pl-5 [&>*+*]:mt-3"
    data-testid="agent-chat-assistant"
    {@attach renderMarkdown}
></div>
