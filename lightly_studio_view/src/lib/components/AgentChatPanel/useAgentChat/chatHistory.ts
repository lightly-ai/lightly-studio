import type { AgentMessage } from '$lib/api/lightly_studio_local';
import { writable } from 'svelte/store';
import { v4 as uuid } from 'uuid';

export interface ChatTurn {
    prompt: string;
    messages: AgentMessage[];
    status: 'running' | 'done' | 'failed';
    error?: string;
    /** When the user sent the prompt, in milliseconds since the epoch. */
    startedAt?: number;
    /** When the reply finished or failed, in milliseconds since the epoch. */
    finishedAt?: number;
}

export interface Conversation {
    id: string;
    updatedAt: number;
    draft: string;
    turns: ChatTurn[];
}

interface HistoryRecord {
    collectionId: string;
    id: string;
    conversation?: Conversation;
    activeId?: string;
    revision?: string;
}

export interface ChatHistory {
    load: (collectionId: string) => Promise<HistoryRecord[]>;
    save: (record: HistoryRecord, previousRevision?: string) => Promise<void>;
}

const STORE = 'conversations';
const ACTIVE = 'active';
export const NEW_CHAT = 'new';
let database: Promise<IDBDatabase> | undefined;

export const chatHistory: ChatHistory = {
    async load(collectionId) {
        const db = await openDatabase();
        const request = db
            .transaction(STORE)
            .objectStore(STORE)
            .index('collectionId')
            .getAll(collectionId);
        return new Promise((resolve, reject) => {
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    },
    async save(record, previousRevision) {
        const db = await openDatabase();
        const transaction = db.transaction(STORE, 'readwrite');
        const store = transaction.objectStore(STORE);
        const existing = store.get([record.collectionId, record.id]);
        existing.onsuccess = () => {
            const saved = existing.result as HistoryRecord | undefined;
            if (record.id !== ACTIVE && saved?.revision !== previousRevision) {
                transaction.abort();
                return;
            }
            store.put(record);
        };
        return new Promise((resolve, reject) => {
            transaction.oncomplete = () => resolve();
            transaction.onabort = () => reject(transaction.error);
        });
    }
};

export const STORAGE_ERROR = 'Chat history could not be saved in this browser.';
export const INTERRUPTED =
    'The reply stopped before it finished. Check the activity before sending again.';
export const STOPPED = 'You stopped the reply.';

export function createChatHistory(collectionId: string, storage: ChatHistory) {
    const conversations = writable<Record<string, Conversation>>({});
    const activeId = writable(NEW_CHAT);
    const revisions = new Map<string, string>();
    const pendingWrites = new Map<string, Promise<void>>();
    const storageError = writable('');
    const ready = storage
        .load(collectionId)
        .then((records) => {
            const restored = records.flatMap(({ conversation }) =>
                conversation ? [[conversation.id, restoreConversation(conversation)]] : []
            );
            for (const { id, revision } of records) {
                if (revision) revisions.set(id, revision);
            }
            conversations.set(Object.fromEntries(restored));
            const lastActive = records.find(({ id }) => id === ACTIVE)?.activeId;
            activeId.set(
                lastActive && restored.some(([id]) => id === lastActive) ? lastActive : NEW_CHAT
            );
        })
        .catch(() => storageError.set('Saved conversations could not be opened in this browser.'));

    function save(record: Omit<HistoryRecord, 'collectionId'>) {
        const { id } = record;
        const revision = uuid();
        const pending = (pendingWrites.get(id) ?? Promise.resolve())
            .then(async () => {
                await storage.save({ collectionId, ...record, revision }, revisions.get(id));
                revisions.set(id, revision);
            })
            .catch(() => storageError.set(STORAGE_ERROR))
            .finally(() => {
                if (pendingWrites.get(id) === pending) pendingWrites.delete(id);
            });
        pendingWrites.set(id, pending);
    }

    function select(id: string) {
        activeId.set(id);
        save({ id: ACTIVE, activeId: id });
    }

    function update(conversation: Conversation) {
        conversations.update((all) => ({ ...all, [conversation.id]: conversation }));
        if (conversation.turns.length || conversation.draft) {
            save({ id: conversation.id, conversation });
        } else {
            // An empty record also clears a previously saved draft.
            save({ id: conversation.id });
        }
    }

    return { conversations, activeId, storageError, ready, select, update };
}

function restoreConversation(conversation: Conversation): Conversation {
    return {
        ...conversation,
        turns: conversation.turns.map((turn) =>
            turn.status === 'running' ? { ...turn, status: 'failed', error: INTERRUPTED } : turn
        )
    };
}

function openDatabase(): Promise<IDBDatabase> {
    database ??= new Promise<IDBDatabase>((resolve, reject) => {
        const request = indexedDB.open('lightly-studio-agent', 1);
        request.onupgradeneeded = () => {
            const store = request.result.createObjectStore(STORE, {
                keyPath: ['collectionId', 'id']
            });
            store.createIndex('collectionId', 'collectionId');
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    }).catch((error) => {
        database = undefined;
        throw error;
    });
    return database;
}
