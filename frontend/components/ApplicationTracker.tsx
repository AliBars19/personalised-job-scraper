"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { createClient } from "@/lib/supabase";
import { StatusSelector } from "./StatusSelector";
import type { Application, ApplicationStatus, Job } from "@/lib/types";
import { useAppStore } from "@/lib/store";

type ApplicationWithJob = Application & { job: Job };

const COLUMNS: { status: ApplicationStatus; label: string; color: string }[] = [
  { status: "saved", label: "Saved", color: "border-yellow-400" },
  { status: "applied", label: "Applied", color: "border-green-400" },
  { status: "interviewing", label: "Interviewing", color: "border-purple-400" },
  { status: "offer", label: "Offer", color: "border-emerald-400" },
  { status: "rejected", label: "Rejected", color: "border-red-400" },
];

export function ApplicationTracker() {
  const [applications, setApplications] = useState<ApplicationWithJob[]>([]);
  const [loading, setLoading] = useState(true);
  const applicationStatuses = useAppStore((s) => s.applicationStatuses);

  useEffect(() => {
    async function fetch() {
      const supabase = createClient();
      const { data, error } = await supabase
        .from("applications")
        .select("*, job:jobs(*)")
        .neq("status", "new")
        .order("updated_at", { ascending: false });

      if (!error && data) {
        setApplications(data as ApplicationWithJob[]);
        const setStatus = useAppStore.getState().setApplicationStatus;
        data.forEach((app) => setStatus(app.job_id, app.status as ApplicationStatus));
      }
      setLoading(false);
    }
    fetch();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  // Get the live status from store (may have been updated by StatusSelector)
  const getStatus = (app: ApplicationWithJob): ApplicationStatus =>
    applicationStatuses[app.job_id] ?? app.status;

  const appliedThisWeek = applications.filter((a) => {
    const status = getStatus(a);
    if (status !== "applied" && status !== "interviewing" && status !== "offer") return false;
    if (!a.applied_at) return false;
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return new Date(a.applied_at) > weekAgo;
  }).length;

  return (
    <div>
      <div className="mb-6 rounded-xl bg-brand-50 p-4 text-sm text-brand-700">
        You&apos;ve applied to <strong>{appliedThisWeek}</strong> job(s) this week
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {COLUMNS.map(({ status, label, color }) => {
          const items = applications.filter((a) => getStatus(a) === status);
          return (
            <div key={status} className={`rounded-xl border-t-4 ${color} bg-white p-4 shadow-sm`}>
              <h3 className="mb-3 text-sm font-semibold text-gray-700">
                {label} ({items.length})
              </h3>
              <div className="space-y-2">
                {items.map((app) => (
                  <motion.div
                    key={app.id}
                    layout
                    className="rounded-lg border border-gray-100 p-3"
                  >
                    <Link
                      href={`/job/${app.job_id}`}
                      className="text-sm font-medium text-gray-900 hover:text-brand-600"
                    >
                      {app.job?.title ?? "Unknown"}
                    </Link>
                    <p className="text-xs text-gray-500">
                      {app.job?.company ?? "Unknown"}
                    </p>
                    {app.notes && (
                      <p className="mt-1 text-xs text-gray-400 italic">{app.notes}</p>
                    )}
                    <div className="mt-2">
                      <StatusSelector
                        jobId={app.job_id}
                        currentStatus={getStatus(app)}
                      />
                    </div>
                  </motion.div>
                ))}
                {items.length === 0 && (
                  <p className="text-xs text-gray-300">No items</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
