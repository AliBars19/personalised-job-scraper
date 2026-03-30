"use client";

import { useCallback, useEffect, useState } from "react";
import { useInView } from "react-intersection-observer";
import { createClient } from "@/lib/supabase";
import { useAppStore } from "@/lib/store";
import { JobCard } from "./JobCard";
import type { ApplicationStatus, Job, JobFilters } from "@/lib/types";

const PAGE_SIZE = 20;

function buildQuery(supabase: ReturnType<typeof createClient>, filters: JobFilters) {
  let query = supabase
    .from("jobs")
    .select("*")
    .eq("is_active", true)
    .is("duplicate_of", null);

  if (filters.category !== "all") {
    query = query.eq("category", filters.category);
  }

  if (filters.salaryMin !== null) {
    query = query.gte("salary_min", filters.salaryMin);
  }

  if (filters.datePosted !== "any") {
    const now = new Date();
    const cutoff = new Date();
    if (filters.datePosted === "24h") cutoff.setDate(now.getDate() - 1);
    else if (filters.datePosted === "7d") cutoff.setDate(now.getDate() - 7);
    else if (filters.datePosted === "30d") cutoff.setDate(now.getDate() - 30);
    query = query.gte("scraped_at", cutoff.toISOString());
  }

  if (filters.search) {
    query = query.or(
      `title.ilike.%${filters.search}%,company.ilike.%${filters.search}%`,
    );
  }

  if (filters.sortBy === "recent") {
    query = query.order("scraped_at", { ascending: false });
  } else if (filters.sortBy === "salary_high") {
    query = query.order("salary_max", { ascending: false, nullsFirst: false });
  } else {
    query = query.order("salary_min", { ascending: true, nullsFirst: false });
  }

  return query;
}

export function JobFeed() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(0);
  const filters = useAppStore((s) => s.filters);
  const applicationStatuses = useAppStore((s) => s.applicationStatuses);

  const { ref: loadMoreRef, inView } = useInView({ threshold: 0 });

  const fetchJobs = useCallback(
    async (pageNum: number, append: boolean) => {
      setLoading(true);
      const supabase = createClient();
      const from = pageNum * PAGE_SIZE;
      const to = from + PAGE_SIZE - 1;

      const { data, error } = await buildQuery(supabase, filters)
        .range(from, to);

      if (error) {
        console.error("Error fetching jobs:", error);
        setLoading(false);
        return;
      }

      const fetched = (data ?? []) as Job[];
      setJobs((prev) => (append ? [...prev, ...fetched] : fetched));
      setHasMore(fetched.length === PAGE_SIZE);
      setLoading(false);
    },
    [filters],
  );

  // Reset when filters change
  useEffect(() => {
    setPage(0);
    setJobs([]);
    setHasMore(true);
    fetchJobs(0, false);
  }, [fetchJobs]);

  // Infinite scroll trigger
  useEffect(() => {
    if (inView && hasMore && !loading) {
      const nextPage = page + 1;
      setPage(nextPage);
      fetchJobs(nextPage, true);
    }
  }, [inView, hasMore, loading, page, fetchJobs]);

  // Fetch application statuses for visible jobs
  useEffect(() => {
    if (jobs.length === 0) return;

    const supabase = createClient();
    const jobIds = jobs.map((j) => j.id);

    supabase
      .from("applications")
      .select("job_id, status")
      .in("job_id", jobIds)
      .then(({ data }) => {
        if (data) {
          const setStatus = useAppStore.getState().setApplicationStatus;
          data.forEach((app) => setStatus(app.job_id, app.status as ApplicationStatus));
        }
      });
  }, [jobs]);

  if (!loading && jobs.length === 0) {
    return (
      <div className="py-20 text-center text-gray-400">
        No jobs found matching your filters.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {jobs.map((job, i) => (
        <JobCard
          key={job.id}
          job={job}
          status={applicationStatuses[job.id] ?? "new"}
          index={i}
        />
      ))}

      {/* Infinite scroll sentinel */}
      {hasMore && (
        <div ref={loadMoreRef} className="flex justify-center py-6">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
        </div>
      )}

      {!hasMore && jobs.length > 0 && (
        <p className="py-6 text-center text-sm text-gray-400">
          You&apos;ve seen all {jobs.length} jobs
        </p>
      )}
    </div>
  );
}
