import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useReversibleActions } from './useReversibleActions';

describe('useReversibleActions', () => {
    let storage: ReturnType<typeof useReversibleActions>;

    beforeEach(() => {
        storage = useReversibleActions();
        storage.clearReversibleActions();
    });

    it('should initially have no reversible actions', () => {
        expect(get(storage.reversibleActions)).toEqual([]);
        expect(storage.hasReversibleActions()).toBe(false);
    });

    it('should add a reversible action', () => {
        const mockExecute = vi.fn();
        const action = {
            id: 'test-action-1',
            description: 'Test action',
            execute: mockExecute,
            timestamp: new Date(),
            groupId: 'test-group'
        };

        storage.addReversibleAction(action);

        const actions = get(storage.reversibleActions);
        expect(actions).toHaveLength(1);
        expect(actions[0]).toEqual(action);
        expect(storage.hasReversibleActions()).toBe(true);
    });

    it('should add multiple reversible actions in reverse chronological order', () => {
        const mockExecute1 = vi.fn();
        const mockExecute2 = vi.fn();
        const action1 = {
            id: 'test-action-1',
            description: 'First action',
            execute: mockExecute1,
            timestamp: new Date('2023-01-01'),
            groupId: 'test-group'
        };
        const action2 = {
            id: 'test-action-2',
            description: 'Second action',
            execute: mockExecute2,
            timestamp: new Date('2023-01-02'),
            groupId: 'test-group'
        };

        storage.addReversibleAction(action1);
        storage.addReversibleAction(action2);

        const actions = get(storage.reversibleActions);
        expect(actions).toHaveLength(2);
        // Most recent action should be first
        expect(actions[0]).toEqual(action2);
        expect(actions[1]).toEqual(action1);
    });

    it('should limit actions to 50 items', () => {
        const mockExecute = vi.fn();

        // Add 55 actions
        for (let i = 0; i < 55; i++) {
            storage.addReversibleAction({
                id: `test-action-${i}`,
                description: `Test action ${i}`,
                execute: mockExecute,
                timestamp: new Date(),
                groupId: 'test-group'
            });
        }

        const actions = get(storage.reversibleActions);
        expect(actions).toHaveLength(50);
        // Should contain the most recent 50 actions (ids 5-54)
        expect(actions[0].id).toBe('test-action-54');
        expect(actions[49].id).toBe('test-action-5');
    });

    it('should execute a reversible action and remove it and subsequent actions', async () => {
        const mockExecute1 = vi.fn().mockResolvedValue(undefined);
        const mockExecute2 = vi.fn().mockResolvedValue(undefined);
        const mockExecute3 = vi.fn().mockResolvedValue(undefined);

        const action1 = {
            id: 'test-action-1',
            description: 'First action',
            execute: mockExecute1,
            timestamp: new Date('2023-01-01'),
            groupId: 'test-group'
        };
        const action2 = {
            id: 'test-action-2',
            description: 'Second action',
            execute: mockExecute2,
            timestamp: new Date('2023-01-02'),
            groupId: 'test-group'
        };
        const action3 = {
            id: 'test-action-3',
            description: 'Third action',
            execute: mockExecute3,
            timestamp: new Date('2023-01-03'),
            groupId: 'test-group'
        };

        storage.addReversibleAction(action1);
        storage.addReversibleAction(action2);
        storage.addReversibleAction(action3);

        // Execute the second action (middle one)
        await storage.executeReversibleAction('test-action-2');

        expect(mockExecute2).toHaveBeenCalledOnce();
        expect(mockExecute1).not.toHaveBeenCalled();
        expect(mockExecute3).not.toHaveBeenCalled();

        // Should keep only actions that were added before the executed action
        const remainingActions = get(storage.reversibleActions);
        expect(remainingActions).toHaveLength(1);
        expect(remainingActions[0].id).toBe('test-action-1');
    });

    it('should handle async execution functions', async () => {
        let executed = false;
        const asyncExecute = vi.fn().mockImplementation(async () => {
            await new Promise((resolve) => setTimeout(resolve, 10));
            executed = true;
        });

        const action = {
            id: 'async-action',
            description: 'Async action',
            execute: asyncExecute,
            timestamp: new Date(),
            groupId: 'async-group'
        };

        storage.addReversibleAction(action);

        await storage.executeReversibleAction('async-action');

        expect(asyncExecute).toHaveBeenCalledOnce();
        expect(executed).toBe(true);
        expect(get(storage.reversibleActions)).toHaveLength(0);
    });

    it('should do nothing when executing non-existent action', async () => {
        const mockExecute = vi.fn();
        const action = {
            id: 'existing-action',
            description: 'Existing action',
            execute: mockExecute,
            timestamp: new Date(),
            groupId: 'test-group'
        };

        storage.addReversibleAction(action);

        await storage.executeReversibleAction('non-existent-action');

        expect(mockExecute).not.toHaveBeenCalled();
        expect(get(storage.reversibleActions)).toHaveLength(1);
    });

    it('should clear all reversible actions', () => {
        const mockExecute = vi.fn();
        const action1 = {
            id: 'test-action-1',
            description: 'First action',
            execute: mockExecute,
            timestamp: new Date(),
            groupId: 'test-group'
        };
        const action2 = {
            id: 'test-action-2',
            description: 'Second action',
            execute: mockExecute,
            timestamp: new Date(),
            groupId: 'test-group'
        };

        storage.addReversibleAction(action1);
        storage.addReversibleAction(action2);

        expect(get(storage.reversibleActions)).toHaveLength(2);
        expect(storage.hasReversibleActions()).toBe(true);

        storage.clearReversibleActions();

        expect(get(storage.reversibleActions)).toHaveLength(0);
        expect(storage.hasReversibleActions()).toBe(false);
    });

    it('should trigger subscribers when actions are added or removed', () => {
        const subscriber = vi.fn();
        storage.reversibleActions.subscribe(subscriber);

        // Reset mock call count (initial subscription call)
        subscriber.mockClear();

        const mockExecute = vi.fn();
        const action = {
            id: 'test-action',
            description: 'Test action',
            execute: mockExecute,
            timestamp: new Date(),
            groupId: 'test-group'
        };

        // Adding an action should trigger subscriber
        storage.addReversibleAction(action);
        expect(subscriber).toHaveBeenCalled();

        // Reset mock call count
        subscriber.mockClear();

        // Clearing actions should trigger subscriber
        storage.clearReversibleActions();
        expect(subscriber).toHaveBeenCalled();
    });

    it('should handle execution with proper action ordering', async () => {
        const executionOrder: string[] = [];

        const createAction = (id: string, timestamp: Date) => ({
            id,
            description: `Action ${id}`,
            execute: vi.fn().mockImplementation(async () => {
                executionOrder.push(id);
            }),
            timestamp,
            groupId: 'test-group'
        });

        const action1 = createAction('1', new Date('2023-01-01'));
        const action2 = createAction('2', new Date('2023-01-02'));
        const action3 = createAction('3', new Date('2023-01-03'));

        storage.addReversibleAction(action1);
        storage.addReversibleAction(action2);
        storage.addReversibleAction(action3);

        // Actions should be in reverse chronological order (newest first)
        const actions = get(storage.reversibleActions);
        expect(actions[0].id).toBe('3');
        expect(actions[1].id).toBe('2');
        expect(actions[2].id).toBe('1');

        // Execute the middle action
        await storage.executeReversibleAction('2');

        expect(executionOrder).toEqual(['2']);

        // Only action 1 should remain (action 3 was removed along with action 2)
        const remainingActions = get(storage.reversibleActions);
        expect(remainingActions).toHaveLength(1);
        expect(remainingActions[0].id).toBe('1');
    });

    it('should clear reversible actions by group ID', () => {
        const mockExecute = vi.fn();
        const action1 = {
            id: 'test-action-1',
            description: 'First action',
            execute: mockExecute,
            timestamp: new Date(),
            groupId: 'group-1'
        };
        const action2 = {
            id: 'test-action-2',
            description: 'Second action',
            execute: mockExecute,
            timestamp: new Date(),
            groupId: 'group-2'
        };
        const action3 = {
            id: 'test-action-3',
            description: 'Third action',
            execute: mockExecute,
            timestamp: new Date(),
            groupId: 'group-1'
        };

        storage.addReversibleAction(action1);
        storage.addReversibleAction(action2);
        storage.addReversibleAction(action3);

        expect(get(storage.reversibleActions)).toHaveLength(3);

        // Clear actions with group-1
        storage.clearReversibleActionsByGroupId('group-1');

        const remainingActions = get(storage.reversibleActions);
        expect(remainingActions).toHaveLength(1);
        expect(remainingActions[0].id).toBe('test-action-2');
        expect(remainingActions[0].groupId).toBe('group-2');
    });

    it('should do nothing when clearing non-existent group ID', () => {
        const mockExecute = vi.fn();
        const action = {
            id: 'test-action',
            description: 'Test action',
            execute: mockExecute,
            timestamp: new Date(),
            groupId: 'existing-group'
        };

        storage.addReversibleAction(action);

        expect(get(storage.reversibleActions)).toHaveLength(1);

        // Clear actions with non-existent group
        storage.clearReversibleActionsByGroupId('non-existent-group');

        expect(get(storage.reversibleActions)).toHaveLength(1);
        expect(get(storage.reversibleActions)[0].id).toBe('test-action');
    });
});
