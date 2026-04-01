"use client";

import { useAppStore } from "@/lib/store";
import type { JobFilters } from "@/lib/types";

const CATEGORIES: { value: JobFilters["category"]; label: string }[] = [
  { value: "all", label: "All" },
  { value: "hospitality", label: "Hospitality" },
  { value: "wine", label: "Wine" },
];

const SALARY_OPTIONS: { value: number | null; label: string }[] = [
  { value: null, label: "Any Salary" },
  { value: 2500000, label: "£25k+" },
  { value: 3500000, label: "£35k+" },
  { value: 4500000, label: "£45k+" },
  { value: 5500000, label: "£55k+" },
];

const DATE_OPTIONS: { value: JobFilters["datePosted"]; label: string }[] = [
  { value: "any", label: "Any Time" },
  { value: "24h", label: "Last 24h" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
];

const SORT_OPTIONS: { value: JobFilters["sortBy"]; label: string }[] = [
  { value: "recent", label: "Most Recent" },
  { value: "salary_high", label: "Salary: High → Low" },
  { value: "salary_low", label: "Salary: Low → High" },
];

export function FilterBar() {
  const { filters, setFilter, resetFilters } = useAppStore();

  return (
    <div className="mb-6 space-y-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      {/* Search */}
      <input
        type="text"
        placeholder="Search jobs..."
        value={filters.search}
        onChange={(e) => setFilter("search", e.target.value)}
        className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
      />

      {/* Category tabs */}
      <div className="flex gap-1">
        {CATEGORIES.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setFilter("category", value)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              filters.category === value
                ? "bg-brand-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Dropdowns row */}
      <div className="flex flex-wrap gap-2">
        <select
          value={filters.salaryMin ?? ""}
          onChange={(e) =>
            setFilter("salaryMin", e.target.value ? Number(e.target.value) : null)
          }
          className="rounded-lg border border-gray-200 px-2 py-1.5 text-sm text-gray-700 focus:border-brand-500 focus:outline-none"
        >
          {SALARY_OPTIONS.map(({ value, label }) => (
            <option key={label} value={value ?? ""}>
              {label}
            </option>
          ))}
        </select>

        <select
          value={filters.datePosted}
          onChange={(e) =>
            setFilter("datePosted", e.target.value as JobFilters["datePosted"])
          }
          className="rounded-lg border border-gray-200 px-2 py-1.5 text-sm text-gray-700 focus:border-brand-500 focus:outline-none"
        >
          {DATE_OPTIONS.map(({ value, label }) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>

        <select
          value={filters.sortBy}
          onChange={(e) =>
            setFilter("sortBy", e.target.value as JobFilters["sortBy"])
          }
          className="rounded-lg border border-gray-200 px-2 py-1.5 text-sm text-gray-700 focus:border-brand-500 focus:outline-none"
        >
          {SORT_OPTIONS.map(({ value, label }) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>

        <button
          onClick={resetFilters}
          className="ml-auto text-sm text-gray-400 hover:text-gray-600"
        >
          Reset
        </button>
      </div>
    </div>
  );
}
