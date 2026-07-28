import escape from 'lodash-es/escape';
import { formatPercent } from '$lib/utils';

type TooltipParams = { name: string; value: number };

/** Builds a tooltip formatter for category-count bar charts. */
export function buildTooltipFormatter(totalCount: number): (params: TooltipParams[]) => string {
    return (params) => {
        if (params.length >= 2) {
            const totalValue = params[0].value; // background series = full count
            const filteredValue = params[1].value; // foreground series = filtered count
            if (totalValue !== filteredValue) {
                const totalPct =
                    totalCount > 0 ? ` (${formatPercent(totalValue / totalCount)})` : '';
                const filteredPct =
                    totalCount > 0 ? ` (${formatPercent(filteredValue / totalCount)})` : '';
                return `<b>${escape(params[0].name)}</b><br/>Total: <b>${totalValue}</b>${totalPct}<br/>In filter: <b>${filteredValue}</b>${filteredPct}`;
            }
        }
        const [{ name, value }] = params;
        const percent = totalCount > 0 ? ` (${formatPercent(value / totalCount)})` : '';
        return `<b>${escape(name)}</b><br/>Count: <b>${value}</b>${percent}`;
    };
}
