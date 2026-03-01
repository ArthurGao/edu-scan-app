"use client";

import { useEffect, useRef, useCallback } from "react";
import type { MathfieldElement } from "mathlive";

interface MathInputProps {
  value: string;
  onChange: (latex: string) => void;
}

export default function MathInput({ value, onChange }: MathInputProps) {
  const ref = useRef<MathfieldElement>(null);
  const readyRef = useRef(false);
  const pendingValueRef = useRef(value);

  // Always keep the latest value in ref so we can sync on ready
  pendingValueRef.current = value;

  const handleInput = useCallback(() => {
    const mf = ref.current;
    if (mf && readyRef.current) onChange(mf.value);
  }, [onChange]);

  // Load MathLive and set up listeners once the custom element is upgraded
  useEffect(() => {
    let cancelled = false;
    import("mathlive").then(() => {
      if (cancelled) return;
      const mf = ref.current;
      if (!mf) return;

      // Wait for the custom element to be defined
      customElements.whenDefined("math-field").then(() => {
        if (cancelled || !ref.current) return;
        readyRef.current = true;

        // Sync any value that was set before we were ready
        if (pendingValueRef.current && mf.value !== pendingValueRef.current) {
          mf.setValue(pendingValueRef.current);
        }

        mf.addEventListener("input", handleInput);

        const handleFocus = () => {
          mf.style.borderColor = "#6366f1";
          mf.style.backgroundColor = "#ffffff";
        };
        const handleBlur = () => {
          mf.style.borderColor = "#d1d5db";
          mf.style.backgroundColor = "#f9fafb";
        };
        mf.addEventListener("focus", handleFocus);
        mf.addEventListener("blur", handleBlur);
      });
    });
    return () => {
      cancelled = true;
      // Remove MathLive virtual keyboard elements from DOM on unmount
      document
        .querySelectorAll("math-virtual-keyboard, .ML__keyboard")
        .forEach((el) => el.remove());
    };
  }, [handleInput]);

  useEffect(() => {
    const mf = ref.current;
    if (mf && readyRef.current && typeof mf.setValue === "function" && mf.value !== value) {
      mf.setValue(value);
    }
  }, [value]);

  return (
    // @ts-expect-error MathLive Web Component not recognized by React JSX types
    <math-field
      ref={ref}
      virtual-keyboard-mode="manual"
      style={{
        width: "100%",
        minHeight: "120px",
        fontSize: "16px",
        borderRadius: "0.75rem",
        border: "2px dashed #d1d5db",
        backgroundColor: "#f9fafb",
        padding: "10px 14px",
        outline: "none",
      }}
    />
  );
}
