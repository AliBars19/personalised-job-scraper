/**
 * Lightweight Supabase REST client for the Chrome extension.
 * Uses fetch directly instead of the full SDK to keep bundle small.
 */

const CorkboardDB = {
  _url: "",
  _key: "",

  async init() {
    const config = await chrome.storage.local.get([
      "supabase_url",
      "supabase_anon_key",
    ]);
    const rawUrl = config.supabase_url || "";
    // Only allow Supabase cloud URLs to prevent key exfiltration
    this._url = /^https:\/\/[a-z0-9]+\.supabase\.co$/.test(rawUrl) ? rawUrl : "";
    this._key = config.supabase_anon_key || "";
  },

  get isConfigured() {
    return Boolean(this._url && this._key);
  },

  _headers() {
    return {
      apikey: this._key,
      Authorization: `Bearer ${this._key}`,
      "Content-Type": "application/json",
      Prefer: "return=representation",
    };
  },

  async query(table, params = {}) {
    const url = new URL(`${this._url}/rest/v1/${table}`);
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));

    const resp = await fetch(url.toString(), { headers: this._headers() });
    if (!resp.ok) throw new Error(`Supabase ${resp.status}: ${resp.statusText}`);
    return resp.json();
  },

  async insert(table, data) {
    const resp = await fetch(`${this._url}/rest/v1/${table}`, {
      method: "POST",
      headers: this._headers(),
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`Supabase insert ${resp.status}`);
    return resp.json();
  },

  async update(table, match, data) {
    const url = new URL(`${this._url}/rest/v1/${table}`);
    Object.entries(match).forEach(([k, v]) =>
      url.searchParams.set(k, `eq.${v}`),
    );

    const resp = await fetch(url.toString(), {
      method: "PATCH",
      headers: this._headers(),
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`Supabase update ${resp.status}`);
    return resp.json();
  },

  async getProfile() {
    const rows = await this.query("user_profile", { limit: "1" });
    return rows[0] || null;
  },

  async getMappings(domain) {
    return this.query("field_mappings", {
      domain: `eq.${domain}`,
    });
  },

  async insertUnmappedField(fieldData) {
    return this.insert("unmapped_fields", fieldData);
  },

  async upsertMapping(mapping) {
    const resp = await fetch(`${this._url}/rest/v1/field_mappings`, {
      method: "POST",
      headers: {
        ...this._headers(),
        Prefer: "resolution=merge-duplicates,return=representation",
      },
      body: JSON.stringify(mapping),
    });
    return resp.json();
  },

  async updateApplicationStatus(jobId, status) {
    // Check if application exists
    const existing = await this.query("applications", {
      job_id: `eq.${jobId}`,
      limit: "1",
    });

    if (existing.length > 0) {
      return this.update("applications", { id: existing[0].id }, {
        status,
        applied_at: status === "applied" ? new Date().toISOString() : undefined,
        updated_at: new Date().toISOString(),
      });
    }

    return this.insert("applications", {
      job_id: jobId,
      status,
      applied_at: status === "applied" ? new Date().toISOString() : undefined,
    });
  },
};
