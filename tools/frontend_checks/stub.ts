// Browser globals the services read at import time (localStorage, sessionStorage, window), for a node run.
const mem: Record<string, string> = {};
(globalThis as any).localStorage = {
  getItem: (k: string) => (k in mem ? mem[k] : null),
  setItem: (k: string, v: string) => { mem[k] = String(v); },
  removeItem: (k: string) => { delete mem[k]; },
  clear: () => { for (const k of Object.keys(mem)) delete mem[k]; },
};
(globalThis as any).sessionStorage = (globalThis as any).localStorage;
(globalThis as any).window = (globalThis as any).window || { location: { search: '' }, addEventListener() {}, matchMedia: () => ({ matches: false }) };
(globalThis as any).document = (globalThis as any).document || { addEventListener() {}, createElement: () => ({}) };
export {};
