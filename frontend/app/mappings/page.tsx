"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase";
import type { FieldMapping } from "@/lib/types";

export default function MappingsPage() {
  const [mappings, setMappings] = useState<FieldMapping[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetch() {
      const supabase = createClient();
      const { data } = await supabase
        .from("field_mappings")
        .select("*")
        .order("domain")
        .order("times_used", { ascending: false });

      if (data) setMappings(data as FieldMapping[]);
      setLoading(false);
    }
    fetch();
  }, []);

  async function handleDelete(id: string) {
    const supabase = createClient();
    await supabase.from("field_mappings").delete().eq("id", id);
    setMappings((prev) => prev.filter((m) => m.id !== id));
  }

  async function toggleVerified(mapping: FieldMapping) {
    const supabase = createClient();
    const updated = !mapping.is_verified;
    await supabase
      .from("field_mappings")
      .update({ is_verified: updated })
      .eq("id", mapping.id);
    setMappings((prev) =>
      prev.map((m) => (m.id === mapping.id ? { ...m, is_verified: updated } : m)),
    );
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  // Group by domain
  const grouped = mappings.reduce<Record<string, FieldMapping[]>>((acc, m) => {
    const key = m.domain;
    if (!acc[key]) acc[key] = [];
    acc[key].push(m);
    return acc;
  }, {});

  return (
    <>
      <h1 className="mb-6 text-xl font-bold text-gray-900">Field Mappings</h1>
      <p className="mb-6 text-sm text-gray-500">
        These mappings tell the Chrome extension how to auto-fill forms on each domain.
      </p>

      {Object.keys(grouped).length === 0 ? (
        <div className="py-20 text-center text-gray-400">
          No field mappings yet. Install the Chrome extension and start applying!
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(grouped).map(([domain, items]) => (
            <div
              key={domain}
              className="rounded-xl border border-gray-200 bg-white shadow-sm"
            >
              <div className="border-b border-gray-100 px-5 py-3">
                <h3 className="font-medium text-gray-900">{domain}</h3>
                <p className="text-xs text-gray-400">{items.length} mapping(s)</p>
              </div>

              <div className="divide-y divide-gray-50">
                {items.map((m) => (
                  <div key={m.id} className="flex items-center gap-3 px-5 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-gray-700">
                        <code className="rounded bg-gray-100 px-1 text-xs">
                          {m.field_selector}
                        </code>
                        {" "}&rarr;{" "}
                        <strong>{m.maps_to}</strong>
                      </p>
                      {m.field_label && (
                        <p className="text-xs text-gray-400">Label: {m.field_label}</p>
                      )}
                    </div>

                    <span className="text-xs text-gray-400">
                      {m.times_used}x
                    </span>

                    <button
                      onClick={() => toggleVerified(m)}
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        m.is_verified
                          ? "bg-green-100 text-green-700"
                          : "bg-yellow-100 text-yellow-700"
                      }`}
                    >
                      {m.is_verified ? "Verified" : "Unverified"}
                    </button>

                    <button
                      onClick={() => handleDelete(m.id)}
                      className="text-xs text-red-400 hover:text-red-600"
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
