type NavigateFn = (to: string, opts?: { replace?: boolean }) => void;

class RouterBridge {
  private _navigate: NavigateFn | null = null;

  register(fn: NavigateFn): void {
    this._navigate = fn;
  }

  navigate(to: string, opts?: { replace?: boolean }): void {
    if (this._navigate) {
      this._navigate(to, opts);
      return;
    }
    if (typeof window !== "undefined") {
      window.location.href = to;
    }
  }

  reset(): void {
    this._navigate = null;
  }
}

export const routerBridge = new RouterBridge();
