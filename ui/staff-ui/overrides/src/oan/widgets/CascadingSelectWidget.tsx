'use client';

/*
 * Region -> Zone -> Woreda -> Kebele dropdowns inside a table row ("Add / Edit row"
 * dialog), like the Crop location section's location picker.
 *
 * A column marked "oan-parent-column" (zz-oan/97b_cascading_location.sql)
 * lists only the children of the value chosen in that column of the same row, and
 * is cleared when that value changes. The platform select already filters a geo
 * level by its parent (dependsOn + level_id -> parent_level_value_id), but it looks
 * the parent up by name, and in the row dialog each cell's value is kept under the
 * cell's own id (`<table>-dlg-<n>-<column>`). This wrapper points dependsOn at the
 * parent cell's id. Every other select, and the table grid, are unchanged.
 */
import { useEffect, useMemo, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { SelectWidget, setValues, type WidgetRootState } from '@openg2p/registry-widgets';

type Config = Record<string, any>;

const PARENT_COLUMN = 'oan-parent-column';

/** The parent cell's widget id in the same dialog row, or null outside a row dialog. */
export function parentCellId(config: Config): string | null {
    const widgetId = String(config['widget-id'] ?? '');
    const column = String(config['column-key'] ?? '');
    const parent = config[PARENT_COLUMN];
    if (!parent || !column || !widgetId.includes('-dlg-') || !widgetId.endsWith(`-${column}`)) return null;
    return `${widgetId.slice(0, widgetId.length - column.length)}${parent}`;
}

export function CascadingSelectWidget({ config }: { config: Config }) {
    const dispatch = useDispatch();
    const widgetId = String(config['widget-id'] ?? '');
    const parentId = parentCellId(config);
    const parentValue = useSelector((state: WidgetRootState) =>
        parentId ? (state.widget.values as Record<string, unknown>)[parentId] : undefined);
    const ownValue = useSelector((state: WidgetRootState) =>
        parentId ? (state.widget.values as Record<string, unknown>)[widgetId] : undefined);

    // A changed parent clears this level, which in turn clears the levels below it.
    // The first value seen (an existing row opened for editing) clears nothing, and
    // neither does a change that set this level together with its parent (the map
    // pin fills Region, Zone and Woreda at once).
    const previous = useRef({ parent: parentValue, own: ownValue });
    useEffect(() => {
        if (!parentId) return;
        const before = previous.current;
        if (before.parent !== undefined && before.parent !== parentValue && before.own === ownValue) {
            dispatch(setValues({ [widgetId]: null } as never));
        }
        previous.current = { parent: parentValue, own: ownValue };
    }, [dispatch, ownValue, parentId, parentValue, widgetId]);

    const effective = useMemo(() => {
        if (!parentId) return config;
        const source = config['widget-data-source'] ?? {};
        return { ...config, 'widget-data-source': { ...source, dependsOn: parentId } };
    }, [config, parentId]);

    return <SelectWidget config={effective as never} />;
}
