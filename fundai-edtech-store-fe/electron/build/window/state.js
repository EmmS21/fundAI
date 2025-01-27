"use strict";
const Store = require('electron-store');
const Types = require('./types');
class WindowStateManager {
    constructor(defaultWidth, defaultHeight) {
        const defaultState = {
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
    get savedState() {
        return this.state;
    }
    saveState(window) {
        if (!window.isDestroyed()) {
            const isMaximized = window.isMaximized();
            if (!isMaximized) {
                const bounds = window.getBounds();
                this.state = Object.assign(Object.assign({}, bounds), { isMaximized });
            }
            else {
                this.state.isMaximized = isMaximized;
            }
            this.store.set('windowState', this.state);
        }
    }
}
module.exports = { WindowStateManager };
