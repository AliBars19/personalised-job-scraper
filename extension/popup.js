document.addEventListener("DOMContentLoaded", async () => {
  const statusDot = document.getElementById("status-dot");
  const statusText = document.getElementById("status-text");
  const profileDot = document.getElementById("profile-dot");
  const profileText = document.getElementById("profile-text");
  const resultsSection = document.getElementById("results-section");
  const resultsContent = document.getElementById("results-content");
  const inputUrl = document.getElementById("input-url");
  const inputKey = document.getElementById("input-key");
  const btnSave = document.getElementById("btn-save");
  const btnFill = document.getElementById("btn-fill");
  const saveMsg = document.getElementById("save-msg");

  // Load saved config
  const config = await chrome.storage.local.get([
    "supabase_url",
    "supabase_anon_key",
  ]);
  inputUrl.value = config.supabase_url || "";
  inputKey.value = config.supabase_anon_key || "";

  // Check connection
  if (config.supabase_url && config.supabase_anon_key) {
    try {
      const resp = await fetch(
        `${config.supabase_url}/rest/v1/user_profile?limit=1`,
        {
          headers: {
            apikey: config.supabase_anon_key,
            Authorization: `Bearer ${config.supabase_anon_key}`,
          },
        },
      );

      if (resp.ok) {
        statusDot.classList.add("green");
        statusText.textContent = "Status: Connected";

        const profiles = await resp.json();
        if (profiles.length > 0 && profiles[0].first_name) {
          profileDot.classList.add("green");
          profileText.textContent = "Profile: Complete";
        } else {
          profileDot.classList.add("yellow");
          profileText.textContent = "Profile: Incomplete";
        }
      } else {
        statusDot.classList.add("red");
        statusText.textContent = "Status: Connection failed";
        profileDot.classList.add("red");
        profileText.textContent = "Profile: N/A";
      }
    } catch {
      statusDot.classList.add("red");
      statusText.textContent = "Status: Error";
      profileDot.classList.add("red");
      profileText.textContent = "Profile: N/A";
    }
  } else {
    statusDot.classList.add("yellow");
    statusText.textContent = "Status: Not configured";
    profileDot.classList.add("yellow");
    profileText.textContent = "Profile: N/A";
  }

  // Check for fill results
  const session = await chrome.storage.session.get("lastFillResults");
  if (session.lastFillResults) {
    const r = session.lastFillResults;
    resultsSection.style.display = "block";
    resultsContent.textContent = "";

    const addRow = (dotColor, text) => {
      const row = document.createElement("div");
      row.className = "result-row";
      const dot = document.createElement("span");
      dot.className = "dot";
      dot.classList.add(dotColor);
      row.appendChild(dot);
      row.appendChild(document.createTextNode(` ${text}`));
      resultsContent.appendChild(row);
    };

    addRow("green", `${Number(r.filled)} field(s) auto-filled`);
    if (r.unmapped > 0) addRow("yellow", `${Number(r.unmapped)} field(s) unmapped`);
    if (r.fileUploads > 0) addRow("yellow", `${Number(r.fileUploads)} file upload(s) — attach manually`);
  }

  // Save config
  btnSave.addEventListener("click", async () => {
    await chrome.storage.local.set({
      supabase_url: inputUrl.value.trim(),
      supabase_anon_key: inputKey.value.trim(),
    });
    saveMsg.textContent = "Saved! Reload the page to use auto-fill.";
    setTimeout(() => (saveMsg.textContent = ""), 3000);
  });

  // Manual fill trigger
  btnFill.addEventListener("click", () => {
    chrome.runtime.sendMessage({ type: "trigger_fill" });
    window.close();
  });

  // Dashboard button
  const btnDashboard = document.getElementById("btn-dashboard");
  btnDashboard.addEventListener("click", () => {
    // Open the frontend dashboard
    const dashUrl = config.supabase_url
      ? config.supabase_url.replace(".supabase.co", "")
      : "http://localhost:3000";
    window.open("http://localhost:3000", "_blank");
  });
});
