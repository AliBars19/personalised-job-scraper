"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { useAppStore } from "@/lib/store";
import { safeUrl } from "@/lib/url";
import { SOURCE_LABELS } from "@/lib/constants";
import { StatusSelector } from "./StatusSelector";
import type { ApplicationStatus, Job } from "@/lib/types";

interface JobCardProps {
  job: Job;
  status: ApplicationStatus;
  index: number;
}

function formatSalary(job: Job): string {
  if (job.salary_text) return job.salary_text;
  if (job.salary_min && job.salary_max) {
    const min = Math.round(job.salary_min / 100).toLocaleString("en-GB");
    const max = Math.round(job.salary_max / 100).toLocaleString("en-GB");
    return `£${min} - £${max}`;
  }
  return "Salary not listed";
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "Today";
  if (days === 1) return "1 day ago";
  if (days < 30) return `${days} days ago`;
  return `${Math.floor(days / 30)}mo ago`;
}

export function JobCard({ job, status, index }: JobCardProps) {
  const { seenJobIds, markSeen } = useAppStore();
  const isSeen = seenJobIds.has(job.id);
  const emoji = job.category === "wine" ? "\uD83C\uDF77" : "\uD83C\uDFE8";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className={`rounded-xl border bg-white p-5 shadow-sm transition-shadow hover:shadow-md ${
        isSeen ? "border-gray-100" : "border-l-4 border-l-brand-500 border-gray-200"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <Link
            href={`/job/${job.id}`}
            onClick={() => markSeen(job.id)}
            className="group"
          >
            <h3 className="text-base font-semibold text-gray-900 group-hover:text-brand-600">
              {emoji} {job.title}
            </h3>
          </Link>

          <p className="mt-1 text-sm text-gray-600">
            {job.company} &middot; {job.location}
          </p>

          <p className="mt-1 text-sm text-gray-500">
            {formatSalary(job)}
            {job.posted_date && (
              <> &middot; {timeAgo(job.posted_date)}</>
            )}
            {!job.posted_date && job.scraped_at && (
              <> &middot; Scraped {timeAgo(job.scraped_at)}</>
            )}
          </p>
        </div>

        <span className="shrink-0 rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
          {SOURCE_LABELS[job.source] ?? job.source}
        </span>
      </div>

      <div className="mt-3 flex items-center justify-between gap-2">
        <StatusSelector jobId={job.id} currentStatus={status} />

        <a
          href={safeUrl(job.application_url || job.source_url)}
          target="_blank"
          rel="noopener noreferrer"
          onClick={() => markSeen(job.id)}
          className="shrink-0 rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-brand-700"
        >
          View &amp; Apply
        </a>
      </div>
    </motion.div>
  );
}
