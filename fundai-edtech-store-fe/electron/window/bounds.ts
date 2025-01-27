import { screen } from 'electron';
import { WindowState } from './types';

export class BoundsValidator {
    static validate(state: WindowState): WindowState {
        const displays = screen.getAllDisplays();
        const visible = displays.some(display => {
            return !(
                state.x! > display.bounds.x + display.bounds.width ||
                state.y! > display.bounds.y + display.bounds.height ||
                state.x! + state.width < display.bounds.x ||
                state.y! + state.height < display.bounds.y
            );
        });

        if (!visible) {
            const primaryDisplay = screen.getPrimaryDisplay();
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
