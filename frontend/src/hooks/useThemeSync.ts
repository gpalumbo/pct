/** Syncs font_size from the project API into uiStore and CSS custom properties. */

import { useEffect } from 'react';
import { useProject } from './useConfigQueries';
import { useUIStore } from '../stores/uiStore';

/** Compute the full --pct-fs-* scale from a base font size (10–20). */
function applyCssScale(base: number) {
  const root = document.documentElement;
  root.style.setProperty('--pct-font-size', `${base}px`);
  root.style.setProperty('--pct-fs-2xs', `${Math.round(base * 0.57)}px`);   // ~8  at 14
  root.style.setProperty('--pct-fs-xs',  `${Math.round(base * 0.71)}px`);   // ~10 at 14
  root.style.setProperty('--pct-fs-sm',  `${Math.round(base * 0.79)}px`);   // ~11 at 14
  root.style.setProperty('--pct-fs-base', `${Math.round(base * 0.86)}px`);  // ~12 at 14
  root.style.setProperty('--pct-fs-md',  `${Math.round(base * 0.93)}px`);   // ~13 at 14
  root.style.setProperty('--pct-fs-lg',  `${base}px`);                      // =14 at 14
  root.style.setProperty('--pct-fs-xl',  `${Math.round(base * 1.14)}px`);   // ~16 at 14
}

export function useThemeSync() {
  const { data: project } = useProject();
  const fontSize = useUIStore((s) => s.fontSize);
  const setFontSize = useUIStore((s) => s.setFontSize);

  // Sync API value → store (when project loads or font_size changes server-side)
  useEffect(() => {
    if (project?.font_size != null && project.font_size !== fontSize) {
      setFontSize(project.font_size);
    }
  }, [project?.font_size]); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync store → CSS variables
  useEffect(() => {
    applyCssScale(fontSize);
  }, [fontSize]);
}
