import { useSyncExternalStore } from 'react';

type StateListener = () => void;

export type StateCreator<T> = (
  set: (partial: Partial<T> | ((state: T) => Partial<T>)) => void,
  get: () => T
) => T;

export interface PersistOptions<T> {
  name: string;
  storage?: Storage;
}

export function create<T>(initializer: StateCreator<T>) {
  let state: T;
  const listeners = new Set<StateListener>();

  const getState = () => state;

  const setState = (partial: Partial<T> | ((s: T) => Partial<T>)) => {
    const nextState = typeof partial === 'function' ? partial(state) : partial;
    if (nextState && typeof nextState === 'object') {
      state = { ...state, ...nextState };
      listeners.forEach((listener) => listener());
    }
  };

  const subscribe = (listener: StateListener) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  };

  state = initializer(setState, getState);

  const useStore = <U = T>(selector?: (s: T) => U): U => {
    return useSyncExternalStore(
      subscribe,
      () => (selector ? selector(state) : (state as unknown as U)),
      () => (selector ? selector(state) : (state as unknown as U))
    );
  };

  useStore.getState = getState;
  useStore.setState = setState;
  useStore.subscribe = subscribe;

  return useStore;
}

export function persist<T>(
  config: StateCreator<T>,
  options: PersistOptions<T>
): StateCreator<T> {
  return (set, get) => {
    const storageKey = options.name;
    const storage = options.storage || (typeof window !== 'undefined' ? window.localStorage : undefined);

    let initialValues: Partial<T> = {};
    if (storage) {
      try {
        const item = storage.getItem(storageKey);
        if (item) {
          const parsed = JSON.parse(item);
          initialValues = parsed.state || parsed;
        }
      } catch {
        // Fallback gracefully on parsing error
      }
    }

    const state = config(
      (partial) => {
        set(partial);
        if (storage) {
          try {
            storage.setItem(storageKey, JSON.stringify({ state: get() }));
          } catch {
            // Ignore quota errors
          }
        }
      },
      get
    );

    return { ...state, ...initialValues };
  };
}
