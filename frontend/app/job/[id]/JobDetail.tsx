"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { createClient } from "@/lib/supabase";
import { StatusSelector } from "@/components/StatusSelector";
import { useAppStore } from "@/lib/store";
import type { Application, ApplicationStatus, Job } from "@/lib/types";

const SOURCE_LABELS: Record<string, string> = {
  indeed: "Indeed",
  reed: "Reed",
  caterer: "Caterer",
  totaljobs: "Totaljobs",
  linkedin: "LinkedIn",
  wine_searcher: "Wine-Searcher",
  harpers: "Harpers",
  hospitality_jobs_uk: "HospitalityJobs",
  drinks_business: "Drinks Business",
};

const APP_TYPE_LABELS: Record<string, string> = {
  easy_apply: "Easy Apply",
  external: "External",
  email: "Email",
  ats_known: "Known ATS",
  unknown: "Unknown",
};

interface JobDetailProps {
  job: Job;
  application: Application | null;
}

export function JobDetail({ job, application }: JobDetailProps) {
  const [notes, setNotes] = useState(application?.notes ?? "");
  const [savingNotes, setSavingNotes] = useState(false);
  const applicationStatuses = useAppStore((s) => s.applicationStatuses);
  const setApplicationStatus = useAppStore((s) => s.setApplicationStatus);

  const currentStatus: ApplicationStatus =
    applicationStatuses[job.id] ?? application?.status ?? "new";

  // Initialize store with server data
  if (application?.status && !applicationStatuses[job.id]) {
    setApplicationStatus(job.id, application.status as ApplicationStatus);
  }

  async function saveNotes() {
    setSavingNotes(true);
    const supabase = createClient();

    if (application?.id) {
      await supabase
        .from("applications")
        .update({ notes, updated_at: new Date().toISOString() })
        .eq("id", application.id);
    } else {
      await supabase.from("applications").insert({
        job_id: job.id,
        status: "new",
        notes,
      });
    }

    setSavingNotes(false);
  }

  const emoji = job.category === "wine" ? "\uD83C\uDF77" : "\uD83C\uDFE8";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h1 className="text-xl font-bold text-gray-900">
          {emoji} {job.title}
        </h1>
        <p className="mt-1 text-gray-600">{job.company} &middot; {job.location}</p>

        <div className="mt-3 flex flex-wrap gap-2">
          {job.salary_text && (
            <span className="rounded-full bg-green-50 px-3 py-1 text-sm text-green-700">
              {job.salary_text}
            </span>
          )}
          <span className="rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-600">
            {SOURCE_LABELS[job.source] ?? job.source}
          </span>
          <span className="rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-600">
            {APP_TYPE_LABELS[job.application_type] ?? job.application_type}
          </span>
        </div>

        <div className="mt-4">
          <StatusSelector jobId={job.id} currentStatus={currentStatus} />
        </div>

        <div className="mt-4">
          <a
            href={job.application_url || job.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block rounded-lg bg-brand-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700"
          >
            Apply Now
          </a>
          <a
            href={job.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-3 inline-block rounded-lg border border-gray-200 px-4 py-2.5 text-sm text-gray-600 transition-colors hover:bg-gray-50"
          >
            View Original
          </a>
        </div>
      </div>

      {/* Description */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Job Description</h2>
        <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
          {job.description || "No description available."}
        </div>
      </div>

      {/* Notes */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Your Notes</h2>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={4}
          placeholder="Add notes about this application..."
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm placeholder:text-gray-300 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
        <button
          onClick={saveNotes}
          disabled={savingNotes}
          className="mt-2 rounded-lg bg-gray-100 px-4 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-200 disabled:opacity-50"
        >
          {savingNotes ? "Saving..." : "Save Notes"}
        </button>
      </div>
    </motion.div>
  );
}
