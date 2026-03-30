/**
 * CorkBoard Field Detection & Auto-Fill Engine.
 *
 * Detects form fields on the page, matches them against:
 *  1. Known field_mappings from Supabase for this domain
 *  2. Smart guessing via autocomplete attributes, name/id patterns, label text
 *
 * Returns fill results so the content script can highlight fields.
 */

const MappingEngine = {
  // HTML autocomplete → user_profile field
  AUTOCOMPLETE_MAP: {
    "given-name": "first_name",
    "family-name": "last_name",
    email: "email",
    tel: "phone",
    "address-line1": "address_line_1",
    "address-line2": "address_line_2",
    "postal-code": "postcode",
    "address-level2": "city",
    country: "country",
    "country-name": "country",
    url: "linkedin_url",
    organization: "current_job_title",
  },

  // Regex patterns for name/id/label/placeholder matching
  NAME_PATTERNS: [
    [/first.?name|fname|given/i, "first_name"],
    [/last.?name|lname|surname|family/i, "last_name"],
    [/email/i, "email"],
    [/phone|tel|mobile/i, "phone"],
    [/address.?1|street|address_line/i, "address_line_1"],
    [/address.?2|apt|suite|unit/i, "address_line_2"],
    [/city|town/i, "city"],
    [/post.?code|zip/i, "postcode"],
    [/country/i, "country"],
    [/linkedin/i, "linkedin_url"],
    [/portfolio|website|personal.?url/i, "portfolio_url"],
    [/salary|compensation|pay/i, "expected_salary"],
    [/notice.?period/i, "notice_period"],
    [/right.?to.?work|visa|eligib|authorized/i, "right_to_work"],
    [/experience|years/i, "years_experience"],
    [/cover.?letter/i, "cover_letter_template"],
    [/job.?title|current.?role|position/i, "current_job_title"],
  ],

  /**
   * Detect all fillable form fields on the page.
   */
  detectFields() {
    const fields = [];
    const inputs = document.querySelectorAll(
      "input, select, textarea",
    );

    for (const el of inputs) {
      if (["hidden", "submit", "button", "reset", "image"].includes(el.type)) {
        continue;
      }

      fields.push({
        element: el,
        selector: this._generateSelector(el),
        type: el.type || el.tagName.toLowerCase(),
        label: this._findLabel(el),
        name: el.name || "",
        id: el.id || "",
        placeholder: el.placeholder || "",
        autocomplete: el.autocomplete || "",
        required: el.required,
      });
    }

    return fields;
  },

  /**
   * Try to guess which user_profile field a form field maps to.
   */
  guessProfileField(fieldInfo) {
    // Priority 1: HTML autocomplete attribute
    if (fieldInfo.autocomplete && this.AUTOCOMPLETE_MAP[fieldInfo.autocomplete]) {
      return this.AUTOCOMPLETE_MAP[fieldInfo.autocomplete];
    }

    // Priority 2: name/id/label/placeholder pattern matching
    const text = [
      fieldInfo.name,
      fieldInfo.id,
      fieldInfo.label,
      fieldInfo.placeholder,
    ].join(" ");

    for (const [pattern, profileField] of this.NAME_PATTERNS) {
      if (pattern.test(text)) {
        return profileField;
      }
    }

    // Priority 3: input type heuristics
    if (fieldInfo.type === "email") return "email";
    if (fieldInfo.type === "tel") return "phone";
    if (fieldInfo.type === "url") return "linkedin_url";

    return null;
  },

  /**
   * Fill a single field with a value.
   */
  fillField(element, value) {
    if (!value && value !== 0) return false;

    const strValue = String(value);

    if (element.tagName === "SELECT") {
      return this._fillSelect(element, strValue);
    }

    // Simulate real user input for React/Angular/Vue compatibility
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype,
      "value",
    )?.set;
    const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype,
      "value",
    )?.set;

    const setter =
      element.tagName === "TEXTAREA"
        ? nativeTextAreaValueSetter
        : nativeInputValueSetter;

    if (setter) {
      setter.call(element, strValue);
    } else {
      element.value = strValue;
    }

    // Fire events to trigger framework reactivity
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
    element.dispatchEvent(new Event("blur", { bubbles: true }));

    return true;
  },

  _fillSelect(selectEl, value) {
    const options = Array.from(selectEl.options);

    // Try exact match first
    let match = options.find(
      (o) => o.value.toLowerCase() === value.toLowerCase(),
    );

    // Then try text content match
    if (!match) {
      match = options.find(
        (o) => o.textContent.trim().toLowerCase() === value.toLowerCase(),
      );
    }

    // Then try includes match
    if (!match) {
      match = options.find(
        (o) =>
          o.textContent.trim().toLowerCase().includes(value.toLowerCase()) ||
          value.toLowerCase().includes(o.textContent.trim().toLowerCase()),
      );
    }

    if (match) {
      selectEl.value = match.value;
      selectEl.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    }

    return false;
  },

  _generateSelector(el) {
    if (el.id) return `#${CSS.escape(el.id)}`;
    if (el.name) return `[name="${CSS.escape(el.name)}"]`;

    // Build path from closest identifiable parent
    const path = [];
    let current = el;
    while (current && current !== document.body) {
      let selector = current.tagName.toLowerCase();
      if (current.id) {
        selector = `#${CSS.escape(current.id)}`;
        path.unshift(selector);
        break;
      }
      const parent = current.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(
          (c) => c.tagName === current.tagName,
        );
        if (siblings.length > 1) {
          const idx = siblings.indexOf(current) + 1;
          selector += `:nth-of-type(${idx})`;
        }
      }
      path.unshift(selector);
      current = parent;
    }

    return path.join(" > ");
  },

  _findLabel(el) {
    // 1. Check for associated <label>
    if (el.id) {
      const label = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (label) return label.textContent.trim();
    }

    // 2. Check parent <label>
    const parentLabel = el.closest("label");
    if (parentLabel) return parentLabel.textContent.trim();

    // 3. Check aria-label
    if (el.getAttribute("aria-label")) {
      return el.getAttribute("aria-label");
    }

    // 4. Check aria-labelledby
    const labelledBy = el.getAttribute("aria-labelledby");
    if (labelledBy) {
      const labelEl = document.getElementById(labelledBy);
      if (labelEl) return labelEl.textContent.trim();
    }

    // 5. Check placeholder
    if (el.placeholder) return el.placeholder;

    return "";
  },
};
