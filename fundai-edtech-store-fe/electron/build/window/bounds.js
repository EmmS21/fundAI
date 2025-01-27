"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.BoundsValidator = void 0;
const electron_1 = require("electron");
class BoundsValidator {
    static validate(state) {
        const displays = electron_1.screen.getAllDisplays();
        const visible = displays.some(display => {
            return !(state.x > display.bounds.x + display.bounds.width ||
                state.y > display.bounds.y + display.bounds.height ||
                state.x + state.width < display.bounds.x ||
                state.y + state.height < display.bounds.y);
        });
        if (!visible) {
            const primaryDisplay = electron_1.screen.getPrimaryDisplay();
            return {
                width: state.width,
                height: state.height,
                x: undefined,
                y: undefined,
                isMaximized: false
            };
        }
        return state;
    }
}
exports.BoundsValidator = BoundsValidator;
