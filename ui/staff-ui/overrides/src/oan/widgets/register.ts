import { widgetRegistry } from '@openg2p/registry-widgets';
import { GeoPointWidget } from './GeoPointWidget';

// Native defaults remain registered; add only the domain map widget.
widgetRegistry.register({ widget: 'oan-geo-point', component: GeoPointWidget as never });

import { IdentityVerificationWidget } from './IdentityVerificationWidget';
widgetRegistry.register({ widget: 'oan-identity-verification', component: IdentityVerificationWidget as never });

// Replaces the native select with a pass-through that adds row-level cascading
// (Region -> Zone -> Woreda -> Kebele) only to table columns marked
// "oan-parent-column"; every other select renders exactly as before.
import { CascadingSelectWidget } from './CascadingSelectWidget';
widgetRegistry.register({ widget: 'select', component: CascadingSelectWidget as never });

// Replaces the native dialog table with a pass-through that adds row limits checked on
// the dialog's Save, only for columns marked "oan-max-column" / "oan-min-column" /
// "oan-max-date-column" (zz-oan/97o_dialog_row_limits.sql); every other table renders
// exactly as before.
import { RowLimitDialogTable } from './RowLimitDialogTable';
widgetRegistry.register({ widget: 'dialog-table', component: RowLimitDialogTable as never });
