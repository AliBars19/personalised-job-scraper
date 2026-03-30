import { create } from "zustand";
import type { ApplicationStatus, JobFilters } from "./types";

interface AppState {
  filters: JobFilters;
  setFilter: <K extends keyof JobFilters>(key: K, value: JobFilters[K]) => void;
  resetFilters: () => void;

  // Track seen jobs locally
  seenJobIds: Set<string>;
  markSeen: (jobId: string) => void;

  // Application status cache (job_id -> status)
  applicationStatuses: Record<string, ApplicationStatus>;
  setApplicationStatus: (jobId: string, status: ApplicationStatus) => void;
}

const DEFAULT_FILTERS: JobFilters = {
  category: "all",
  salaryMin: null,
  datePosted: "any",
  source: "all",
  status: "all",
  sortBy: "recent",
  search: "",
};

export const useAppStore = create<AppState>((set) => ({
  filters: { ...DEFAULT_FILTERS },

  setFilter: (key, value) =>
    set((state) => ({
      filters: { ...state.filters, [key]: value },
    })),

  resetFilters: () =>
    set({ filters: { ...DEFAULT_FILTERS } }),

  seenJobIds: new Set<string>(),
  markSeen: (jobId) =>
    set((state) => {
      const next = new Set(state.seenJobIds);
      next.add(jobId);
      return { seenJobIds: next };
    }),

  applicationStatuses: {},
  setApplicationStatus: (jobId, status) =>
    set((state) => ({
      applicationStatuses: { ...state.applicationStatuses, [jobId]: status },
    })),
}));
