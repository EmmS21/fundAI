const Store = require('electron-store');
const Types = require('./types');

class WindowStateManager {
    /** @type {any} */
    store;
    /** @type {import('./types').WindowState} */
    state;

    constructor(defaultWidth: number, defaultHeight: number) {
        const defaultState: typeof Types.WindowState = {
            width: defaultWidth,
            height: defaultHeight,
            x: undefined,
            y: undefined,
            isMaximized: false
        };

        this.store = new Store({
            name: 'window-state',
            defaults: {
                windowState: defaultState
            }
        });

        this.state = this.store.get('windowState');
    }

    get savedState(): typeof Types.WindowState {
        return this.state;
    }

    saveState(window: Electron.BrowserWindow): void {
        if (!window.isDestroyed()) {
            const isMaximized = window.isMaximized();
            
            if (!isMaximized) {
                const bounds = window.getBounds();
                this.state = {
                    ...bounds,
                    isMaximized
                };
            } else {
                this.state.isMaximized = isMaximized;
            }

            this.store.set('windowState', this.state);
        }
    }
}

module.exports = { WindowStateManager };
