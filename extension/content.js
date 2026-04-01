/**
 * CorkBoard Content Script.
 *
 * Injected into every page. Activates when it detects:
 *  - A corkboard_job_id URL parameter (came from the dashboard)
 *  - A message from the background script
 *
 * Then auto-fills the form using MappingEngine + Supabase data.
 */

(async function () {
  "use strict";

  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  const url = new URL(window.location.href);
  const rawJobId = url.searchParams.get("corkboard_job_id");
  const jobId = rawJobId && UUID_RE.test(rawJobId) ? rawJobId : null;
  const domain = window.location.hostname;

  // Only activate if triggered from CorkBoard dashboard
  const isTriggered = jobId || (await checkBackgroundTrigger());
  if (!isTriggered) return;

  await CorkboardDB.init();
  if (!CorkboardDB.isConfigured) {
    console.log("[CorkBoard] Not configured — open extension popup to set up.");
    return;
  }

  // Wait a moment for dynamic forms to render
  await sleep(1500);

  const profile = await CorkboardDB.getProfile();
  if (!profile) {
    console.log("[CorkBoard] No profile found — set up your profile first.");
    return;
  }

  const ALLOWED_PROFILE_FIELDS = new Set([
    "first_name", "last_name", "email", "phone", "address_line_1",
    "address_line_2", "city", "postcode", "country", "linkedin_url",
    "portfolio_url", "current_job_title", "years_experience",
    "right_to_work", "notice_period", "expected_salary",
    "cover_letter_template",
  ]);

  const existingMappings = await CorkboardDB.getMappings(domain);
  const mappingsBySelector = {};
  for (const m of existingMappings) {
    if (ALLOWED_PROFILE_FIELDS.has(m.maps_to)) {
      mappingsBySelector[m.field_selector] = m;
    }
  }

  const fields = MappingEngine.detectFields();

  let filledCount = 0;
  let unmappedCount = 0;
  let fileUploadCount = 0;
  const unmappedFields = [];

  for (const field of fields) {
    // Skip file inputs
    if (field.type === "file") {
      fileUploadCount++;
      highlightField(field.element, "file");
      continue;
    }

    // 1. Check existing DB mappings
    const dbMapping = mappingsBySelector[field.selector];
    if (dbMapping) {
      const value = profile[dbMapping.maps_to];
      if (value !== undefined && value !== null) {
        const filled = MappingEngine.fillField(field.element, value);
        if (filled) {
          filledCount++;
          highlightField(field.element, "filled");

          // Update usage stats
          CorkboardDB.update(
            "field_mappings",
            { id: dbMapping.id },
            {
              last_used: new Date().toISOString(),
              times_used: (dbMapping.times_used || 0) + 1,
            },
          ).catch(() => {});

          continue;
        }
      }
    }

    // 2. Try smart guessing
    const guessedField = MappingEngine.guessProfileField(field);
    if (guessedField && profile[guessedField] !== undefined && profile[guessedField] !== null) {
      const filled = MappingEngine.fillField(field.element, profile[guessedField]);
      if (filled) {
        filledCount++;
        highlightField(field.element, "filled");

        // Save the new mapping (unverified)
        CorkboardDB.upsertMapping({
          domain,
          field_selector: field.selector,
          field_type: field.type,
          field_label: field.label,
          maps_to: guessedField,
          is_verified: false,
        }).catch(() => {});

        continue;
      }
    }

    // 3. Unmapped field
    unmappedCount++;
    unmappedFields.push(field);
    highlightField(field.element, "unmapped");
  }

  // Log unmapped fields to Supabase for review
  for (const field of unmappedFields) {
    CorkboardDB.insertUnmappedField({
      domain,
      page_url: window.location.origin + window.location.pathname,
      field_selector: field.selector,
      field_type: field.type,
      field_label: field.label,
      field_name: field.name,
      field_placeholder: field.placeholder,
    }).catch(() => {});
  }

  // Send results to popup
  chrome.runtime.sendMessage({
    type: "fill_results",
    data: {
      filled: filledCount,
      unmapped: unmappedCount,
      fileUploads: fileUploadCount,
      domain,
      jobId,
    },
  });

  // Listen for form submission to mark as applied
  detectFormSubmission(jobId);

  console.log(
    `[CorkBoard] Auto-fill complete: ${filledCount} filled, ${unmappedCount} unmapped, ${fileUploadCount} file upload(s)`,
  );
})();

function highlightField(element, type) {
  const colors = {
    filled: { border: "#22c55e", bg: "rgba(34, 197, 94, 0.05)" },
    unmapped: { border: "#eab308", bg: "rgba(234, 179, 8, 0.05)" },
    file: { border: "#3b82f6", bg: "rgba(59, 130, 246, 0.05)" },
  };

  const style = colors[type] || colors.unmapped;
  element.style.outline = `2px solid ${style.border}`;
  element.style.backgroundColor = style.bg;

  if (type === "file") {
    const reminder = document.createElement("div");
    reminder.className = "corkboard-cv-reminder";
    reminder.textContent = "\uD83D\uDCCE Don't forget to attach your CV!";
    reminder.style.cssText =
      "color:#3b82f6;font-size:12px;font-weight:600;margin-top:4px;";
    element.parentElement?.appendChild(reminder);
  }
}

function detectFormSubmission(jobId) {
  if (!jobId) return;

  document.addEventListener("submit", () => {
    CorkboardDB.updateApplicationStatus(jobId, "applied").catch(() => {});
  });

  // Also detect button clicks that might submit (SPAs)
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(
      'button[type="submit"], input[type="submit"], a[class*="submit"], button[class*="apply"]',
    );
    if (btn) {
      setTimeout(() => {
        CorkboardDB.updateApplicationStatus(jobId, "applied").catch(() => {});
      }, 2000);
    }
  });
}

async function checkBackgroundTrigger() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: "check_trigger" }, (response) => {
      resolve(response?.triggered === true);
    });
  });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
