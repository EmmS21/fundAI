declare module 'electron-store' {
    interface StoreOptions<T> {
        name?: string;
        defaults?: T;
    }

    class Store<T extends Record<string, any>> {
        constructor(options?: StoreOptions<T>);
        get<K extends keyof T>(key: K): T[K];
        set<K extends keyof T>(key: K, value: T[K]): void;
    }

    export = Store;
}
