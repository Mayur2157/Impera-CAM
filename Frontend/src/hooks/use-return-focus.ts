import { useEffect, useState } from "react";

/** Render inside a dialog's content. Remembers what had focus when the dialog opened and
 *  puts focus back there after it closes — dialogs opened from state (not a Radix Trigger)
 *  otherwise drop focus to <body>. */
export function ReturnFocus() {
  const [prev] = useState(() => (typeof document !== "undefined" ? (document.activeElement as HTMLElement | null) : null));
  useEffect(() => () => {
    setTimeout(() => {
      const a = document.activeElement;
      if (prev && prev.isConnected && prev !== document.body && (!a || a === document.body)) prev.focus();
    }, 50);
  }, [prev]);
  return null;
}
