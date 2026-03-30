"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase";
import type { UserProfile } from "@/lib/types";

const FIELDS: { key: keyof UserProfile; label: string; type?: string; rows?: number }[] = [
  { key: "first_name", label: "First Name" },
  { key: "last_name", label: "Last Name" },
  { key: "email", label: "Email", type: "email" },
  { key: "phone", label: "Phone", type: "tel" },
  { key: "address_line_1", label: "Address Line 1" },
  { key: "address_line_2", label: "Address Line 2" },
  { key: "city", label: "City" },
  { key: "postcode", label: "Postcode" },
  { key: "country", label: "Country" },
  { key: "linkedin_url", label: "LinkedIn URL", type: "url" },
  { key: "portfolio_url", label: "Portfolio URL", type: "url" },
  { key: "current_job_title", label: "Current Job Title" },
  { key: "years_experience", label: "Years of Experience", type: "number" },
  { key: "right_to_work", label: "Right to Work in UK" },
  { key: "notice_period", label: "Notice Period" },
  { key: "expected_salary", label: "Expected Salary" },
  { key: "cover_letter_template", label: "Cover Letter Template", rows: 6 },
];

export function ProfileForm() {
  const [profile, setProfile] = useState<Partial<UserProfile>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function loadProfile() {
      const supabase = createClient();
      const { data } = await supabase
        .from("user_profile")
        .select("*")
        .limit(1)
        .single();

      if (data) {
        setProfile(data as UserProfile);
      }
      setLoading(false);
    }
    loadProfile();
  }, []);

  async function handleSave() {
    setSaving(true);
    setMessage("");

    const supabase = createClient();
    const payload = {
      ...profile,
      updated_at: new Date().toISOString(),
    };

    // Upsert: update if exists, insert if not
    if (profile.id) {
      const { error } = await supabase
        .from("user_profile")
        .update(payload)
        .eq("id", profile.id);
      if (error) {
        setMessage("Error saving profile");
      } else {
        setMessage("Profile saved!");
      }
    } else {
      const { data, error } = await supabase
        .from("user_profile")
        .insert(payload)
        .select()
        .single();
      if (error) {
        setMessage("Error creating profile");
      } else {
        setProfile(data as UserProfile);
        setMessage("Profile created!");
      }
    }

    setSaving(false);
    setTimeout(() => setMessage(""), 3000);
  }

  function handleChange(key: string, value: string | number) {
    setProfile((prev) => ({ ...prev, [key]: value }));
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <h2 className="mb-6 text-lg font-semibold text-gray-900">Your Profile</h2>
      <p className="mb-6 text-sm text-gray-500">
        This data is used by the Chrome extension to auto-fill job applications.
      </p>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {FIELDS.map(({ key, label, type, rows }) => (
          <div key={key} className={rows ? "md:col-span-2" : ""}>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              {label}
            </label>
            {rows ? (
              <textarea
                rows={rows}
                value={(profile[key] as string) ?? ""}
                onChange={(e) => handleChange(key, e.target.value)}
                placeholder={`Use {company_name} and {job_title} as placeholders`}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm placeholder:text-gray-300 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            ) : (
              <input
                type={type ?? "text"}
                value={(profile[key] as string) ?? ""}
                onChange={(e) =>
                  handleChange(
                    key,
                    type === "number" ? Number(e.target.value) : e.target.value,
                  )
                }
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            )}
          </div>
        ))}
      </div>

      <div className="mt-6 flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-lg bg-brand-600 px-6 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save Profile"}
        </button>
        {message && (
          <span className="text-sm text-green-600">{message}</span>
        )}
      </div>
    </div>
  );
}
