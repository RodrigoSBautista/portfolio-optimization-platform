import { Toaster } from "sonner";
import { useTheme } from "../theme/useTheme";

// Single sonner <Toaster>, themed to match the active light/dark palette. The
// toast surfaces reuse the Tailwind theme tokens so colors stay consistent.
export function ThemedToaster() {
  const { theme } = useTheme();
  return (
    <Toaster
      theme={theme}
      position="bottom-right"
      richColors
      closeButton
      toastOptions={{
        style: {
          borderRadius: "0.75rem",
          fontSize: "0.875rem",
        },
      }}
    />
  );
}
