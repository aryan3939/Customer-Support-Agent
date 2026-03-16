"use client";

import { createContext, useContext } from "react";

// Sidebar state context — shared so child pages can react to collapse state
export const SidebarContext = createContext({
  collapsed: false,
  toggle: () => {},
});

export function useSidebar() {
  return useContext(SidebarContext);
}
