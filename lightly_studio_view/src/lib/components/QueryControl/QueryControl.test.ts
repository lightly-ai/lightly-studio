import { expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import QueryControl from './QueryControl.svelte';

const expression = {
    query_expr: { match_expr: { type: 'and' as const, children: [] } },
    query_expr_str: 'width > 100'
};

it('opens, disables, restores, and clears the current query', async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    const updateQueryExpr = vi.fn();
    const { rerender } = render(QueryControl, {
        props: { onOpen, updateQueryExpr, queryExpression: null }
    });
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();

    await rerender({ queryExpression: expression });
    expect(screen.getByRole('checkbox', { name: 'Disable query filter' })).toBeChecked();
    await user.click(screen.getByRole('button', { name: /^Query Filter/ }));
    expect(onOpen).toHaveBeenCalledOnce();

    await user.click(screen.getByRole('checkbox', { name: 'Disable query filter' }));
    expect(updateQueryExpr).toHaveBeenLastCalledWith(undefined);
    await rerender({ queryExpression: null });
    expect(screen.getByText(expression.query_expr_str)).toBeVisible();
    expect(screen.getByRole('checkbox', { name: 'Enable query filter' })).not.toBeChecked();

    await user.click(screen.getByRole('checkbox', { name: 'Enable query filter' }));
    expect(updateQueryExpr).toHaveBeenLastCalledWith(expression);
    await rerender({ queryExpression: expression });

    await user.click(screen.getByRole('button', { name: 'Clear query filter' }));
    expect(updateQueryExpr).toHaveBeenLastCalledWith(undefined);
    await rerender({ queryExpression: null });
    expect(screen.queryByText(expression.query_expr_str)).not.toBeInTheDocument();
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
});
