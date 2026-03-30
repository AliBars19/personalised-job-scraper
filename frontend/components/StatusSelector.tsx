"use client";

import { createClient } from "@/lib/supabase";
import { useAppStore } from "@/lib/store";
import type { ApplicationStatus } from "@/lib/types";

const STATUS_OPTIONS: { value: ApplicationStatus; label: string; color: string }[] = [
  { value: "new", label: "New", color: "bg-blue-100 text-blue-700" },
  { value: "saved", label: "Saved", color: "bg-yellow-100 text-yellow-700" },
  { value: "applied", label: "Applied", color: "bg-green-100 text-green-700" },
  { value: "interviewing", label: "Interviewing", color: "bg-purple-100 text-purple-700" },
  { value: "rejected", label: "Rejected", color: "bg-red-100 text-red-700" },
  { value: "offer", label: "Offer", color: "bg-emerald-100 text-emerald-700" },
];

interface StatusSelectorProps {
  jobId: string;
  currentStatus: ApplicationStatus;
}

export function StatusSelector({ jobId, currentStatus }: StatusSelectorProps) {
  const setApplicationStatus = useAppStore((s) => s.setApplicationStatus);

  async function handleChange(newStatus: ApplicationStatus) {
    if (newStatus === currentStatus) return;

    const previousStatus = currentStatus;
    setApplicationStatus(jobId, newStatus);

    try {
      const supabase = createClient();

      const { data: existing } = await supabase
        .from("applications")
        .select("id")
        .eq("job_id", jobId)
        .limit(1)
        .single();

      if (existing) {
        const { error } = await supabase
          .from("applications")
          .update({
            status: newStatus,
            applied_at: newStatus === "applied" ? new Date().toISOString() : undefined,
            updated_at: new Date().toISOString(),
          })
          .eq("id", existing.id);
        if (error) throw error;
      } else {
        const { error } = await supabase.from("applications").insert({
          job_id: jobId,
          status: newStatus,
          applied_at: newStatus === "applied" ? new Date().toISOString() : undefined,
        });
        if (error) throw error;
      }
    } catch {
      // Rollback optimistic update on failure
      setApplicationStatus(jobId, previousStatus);
    }
  }

  return (
    <div className="flex flex-wrap gap-1">
      {STATUS_OPTIONS.map(({ value, label, color }) => (
        <button
          key={value}
          onClick={() => handleChange(value)}
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition-all ${
            currentStatus === value
              ? `${color} ring-2 ring-offset-1`
              : "bg-gray-100 text-gray-500 hover:bg-gray-200"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
