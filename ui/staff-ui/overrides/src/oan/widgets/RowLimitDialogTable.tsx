'use client';

/*
 * Row limits checked in the "Add / Edit row" dialog, on Save, before a row reaches the
 * table, by comparing two fields of the same row. zz-oan/97o_dialog_row_limits.sql marks
 * the columns (Planning, Cultivation, Cluster, Cultivation cluster, Sowing, Harvest):
 *   "oan-max-column"       not more than that column, times "oan-max-factor" if given
 *   "oan-plus-column"      added to this column's value before that comparison
 *   "oan-min-column"       a date not earlier than that column
 *   "oan-max-date-column"  a date not later than that column
 *   "oan-limit-message"    the translation key of the message ({limit}: the other value)
 *
 * The platform's dialog Save already refuses a row whose cells fail their
 * "widget-data-validation", showing the messages of a zod schema there. This wrapper adds
 * one such schema to each marked column; it reads the other columns of the row being
 * edited from the dialog's cells (`<table>-dlg-<session>-<column>`, the newest session is
 * the open dialog). Blank values, and an other column hidden in that row by its show rule
 * (Total land area when "Is planning record created?" is Yes), are not compared. Unmarked
 * columns and tables render exactly as before. The server keeps the same rules on Next.
 */
import { useMemo } from 'react';
import { useSelector, useStore } from 'react-redux';
import { useTranslations } from 'next-intl';
import { z } from 'zod';
import { DialogTableWidget, type WidgetRootState } from '@openg2p/registry-widgets';

type Config = Record<string, any>;

const MAX_COLUMN = 'oan-max-column';
const MAX_FACTOR = 'oan-max-factor';
const PLUS_COLUMN = 'oan-plus-column';
const MIN_COLUMN = 'oan-min-column';
const MAX_DATE_COLUMN = 'oan-max-date-column';
const MESSAGE = 'oan-limit-message';
const MARKS = [MAX_COLUMN, MIN_COLUMN, MAX_DATE_COLUMN];
// Location levels (zz-oan/97b_cascading_location.sql and the land-row overlays): Zone,
// Woreda and Kebele name the column above them.
const PARENT_COLUMN = 'oan-parent-column';

/** The open row dialog's session of table `tableId` (the newest one), or -1 when none. */
export function openSession(values: Record<string, unknown>, tableId: string): number {
    const prefix = `${tableId}-dlg-`;
    let newest = -1;
    for (const key of Object.keys(values)) {
        if (!key.startsWith(prefix)) continue;
        const session = Number(key.slice(prefix.length).split('-')[0]);
        if (Number.isInteger(session) && session > newest) newest = session;
    }
    return newest;
}

/** The value of `column` in the open row dialog of table `tableId` (the newest dialog session). */
export function openRowValue(values: Record<string, unknown>, tableId: string, column: string): unknown {
    const prefix = `${tableId}-dlg-`;
    const suffix = `-${column}`;
    let newest = -1;
    let found: unknown;
    for (const [key, value] of Object.entries(values)) {
        if (!key.startsWith(prefix) || !key.endsWith(suffix)) continue;
        const session = Number(key.slice(prefix.length, key.length - suffix.length));
        if (Number.isInteger(session) && session > newest) {
            newest = session;
            found = value;
        }
    }
    return found;
}

const blank = (value: unknown) => value === null || value === undefined || String(value).trim() === '';

/** True when a number is more than a positive limit (both given). */
export function aboveLimit(value: unknown, limit: unknown): boolean {
    if (blank(value) || blank(limit)) return false;
    const number = Number(value);
    const max = Number(limit);
    return Number.isFinite(number) && Number.isFinite(max) && max > 0 && number > max + 1e-9;
}

/** True when a YYYY-MM-DD date is earlier than another (both given). */
export function beforeLimit(value: unknown, limit: unknown): boolean {
    const day = String(value ?? '').slice(0, 10);
    const min = String(limit ?? '').slice(0, 10);
    const iso = /^\d{4}-\d{2}-\d{2}$/;
    return iso.test(day) && iso.test(min) && day < min;
}

const asBool = (value: unknown): boolean | null => {
    if (value === true || value === 1) return true;
    if (value === false || value === 0) return false;
    const text = String(value ?? '').trim().toLowerCase();
    if (['true', 'yes', '1'].includes(text)) return true;
    if (['false', 'no', '0'].includes(text)) return false;
    return null;
};

/** A column's show rule ({field, operator, value}) against the row; no rule: shown. */
export function shownInRow(column: Config | undefined, row: (key: string) => unknown): boolean {
    const rule = column?.['widget-data-options']?.condition;
    if (!rule || typeof rule !== 'object' || !rule.field) return true;
    const actual = row(rule.field);
    const equal = () => (typeof rule.value === 'boolean' ? asBool(actual) === rule.value : actual === rule.value);
    switch (rule.operator) {
        case 'equals':
            return equal();
        case 'notEquals':
            return !equal();
        case 'contains': {
            const items = Array.isArray(actual) ? actual : blank(actual) ? [] : [actual];
            const wanted = String(rule.value).toUpperCase();
            return items.some((item) => String(item && typeof item === 'object' ? (item.value ?? item.label) : item)
                .toUpperCase().includes(wanted));
        }
        default:
            return true;
    }
}

const shown = (limit: unknown) => String(Math.round(Number(limit) * 10000) / 10000);

export function RowLimitDialogTable({ config }: { config: Config }) {
    const store = useStore<WidgetRootState>();
    const t = useTranslations();
    const tableId = String(config['widget-id'] ?? '');

    // The open dialog's session and its location parents' values, as one string so the
    // dialog re-renders only when one of them changes.
    const parentColumns = useMemo(() => {
        const columns = config['widget-data-columns'];
        return Array.isArray(columns)
            ? Array.from(new Set(columns.map((c: Config) => c?.[PARENT_COLUMN]).filter(Boolean).map(String)))
            : [];
    }, [config]);
    const parents = useSelector((state: WidgetRootState) => {
        if (parentColumns.length === 0) return '';
        const values = (state.widget?.values ?? {}) as Record<string, unknown>;
        const session = openSession(values, tableId);
        if (session < 0) return '';
        return JSON.stringify([session, parentColumns.map((p) => values[`${tableId}-dlg-${session}-${p}`] ?? null)]);
    });

    const effective = useMemo(() => {
        const original = config['widget-data-columns'];
        if (!Array.isArray(original)) return config;
        // Location levels in the open dialog: nothing to choose until the level above is chosen
        // ("Select" only), then that parent's children. The platform loads a field's list from
        // the column as given here, before any field widget runs, so it is set on the column.
        let columns = original;
        if (parents) {
            const [session, parentValues] = JSON.parse(parents) as [number, unknown[]];
            columns = original.map((col: Config) => {
                const parent = col?.[PARENT_COLUMN];
                const source = col?.['widget-data-source'];
                if (!parent || !source) return col;
                const value = parentValues[parentColumns.indexOf(String(parent))];
                return blank(value)
                    ? { ...col, 'widget-data-source': { type: 'static', options: [] } }
                    : { ...col, 'widget-data-source': { ...source, dependsOn: `${tableId}-dlg-${session}-${parent}` } };
            });
        }
        if (!columns.some((c) => MARKS.some((mark) => c?.[mark]))) {
            return columns === original ? config : { ...config, 'widget-data-columns': columns };
        }
        const byKey = new Map<string, Config>(columns.map((c: Config) => [String(c?.['column-key']), c]));
        // Read at Save time from the store, so the check always sees the row as it is now.
        const row = (column: string) =>
            openRowValue((store.getState().widget?.values ?? {}) as Record<string, unknown>, tableId, column);
        const visible = (column: string) => shownInRow(byKey.get(column), row);
        const message = (col: Config, limit: unknown, fallback: string) => {
            const key = col[MESSAGE];
            return key && t.has(key) ? t(key, { limit: String(limit) }) : fallback;
        };
        return {
            ...config,
            'widget-data-columns': columns.map((col: Config) => {
                if (!MARKS.some((mark) => col?.[mark])) return col;
                const schema = z.any().superRefine((value, ctx) => {
                    const fail = (limit: unknown, fallback: string) =>
                        ctx.addIssue({ code: 'custom', message: message(col, limit, fallback) });
                    const maxColumn = col[MAX_COLUMN];
                    if (maxColumn && visible(maxColumn)) {
                        const other = row(maxColumn);
                        const factor = Number(col[MAX_FACTOR] ?? 1);
                        const limit = blank(other) ? other : Number(other) * (Number.isFinite(factor) ? factor : 1);
                        const plus = col[PLUS_COLUMN];
                        const added = plus && visible(plus) && !blank(row(plus)) ? Number(row(plus)) : 0;
                        const total = blank(value) ? value : Number(value) + (Number.isFinite(added) ? added : 0);
                        if (aboveLimit(total, limit)) fail(shown(limit), `Cannot be more than ${shown(limit)}`);
                    }
                    const minColumn = col[MIN_COLUMN];
                    if (minColumn && visible(minColumn) && beforeLimit(value, row(minColumn))) {
                        fail(row(minColumn), `Cannot be earlier than ${row(minColumn)}`);
                    }
                    const maxDateColumn = col[MAX_DATE_COLUMN];
                    if (maxDateColumn && visible(maxDateColumn) && beforeLimit(row(maxDateColumn), value)) {
                        fail(row(maxDateColumn), `Cannot be later than ${row(maxDateColumn)}`);
                    }
                });
                return { ...col, 'widget-data-validation': { ...(col['widget-data-validation'] ?? {}), zodSchema: schema } };
            }),
        };
    }, [config, store, tableId, t, parents, parentColumns]);

    return <DialogTableWidget config={effective as never} />;
}
