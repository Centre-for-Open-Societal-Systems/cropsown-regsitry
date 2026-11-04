import { createElement } from 'react';
import { DateInputWidget, widgetRegistry } from '@openg2p/registry-widgets';
import {
    ETHIOPIAN_DATE_CELL,
    ETHIOPIAN_DATE_VARIANT,
    EthiopianDateInputWidget,
} from './EthiopianDateInputWidget';
import { GeoPointWidget } from './GeoPointWidget';

type Props = { config: Record<string, unknown> } & Record<string, unknown>;

function DateOrVariant(props: Props) {
    if (props.config['widget-variant'] === ETHIOPIAN_DATE_VARIANT) {
        return createElement(EthiopianDateInputWidget, props as never);
    }
    return createElement(DateInputWidget, props as never);
}

// Preserve the native date widget unless metadata explicitly asks for the
// Ethiopian entry variant. Table date cells need a custom widget type because
// the upstream TableCellDate does not inspect widget variants.
widgetRegistry.register({ widget: 'date', component: DateOrVariant });
widgetRegistry.register({ widget: ETHIOPIAN_DATE_CELL, component: EthiopianDateInputWidget as never });

// Native defaults remain registered; add the domain widgets.
widgetRegistry.register({ widget: 'oan-geo-point', component: GeoPointWidget as never });

import { IdentityVerificationWidget } from './IdentityVerificationWidget';
widgetRegistry.register({ widget: 'oan-identity-verification', component: IdentityVerificationWidget as never });
