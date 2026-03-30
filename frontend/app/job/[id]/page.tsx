import { notFound } from "next/navigation";
import { createServerSupabase } from "@/lib/supabase-server";
import { JobDetail } from "./JobDetail";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function JobPage({ params }: PageProps) {
  const { id } = await params;
  const supabase = await createServerSupabase();

  const { data: job } = await supabase
    .from("jobs")
    .select("*")
    .eq("id", id)
    .single();

  if (!job) {
    notFound();
  }

  const { data: application } = await supabase
    .from("applications")
    .select("*")
    .eq("job_id", id)
    .limit(1)
    .single();

  return <JobDetail job={job} application={application} />;
}
