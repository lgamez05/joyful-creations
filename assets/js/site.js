/* Joyful Creations LI
   No analytics. No pixels. No network submit.
   Planned event names for a future ads phase are not sent. */
(function () {
  "use strict";

  var PLANNED_EVENTS = Object.freeze({
    ViewContent: "ViewContent",
    Lead: "Lead",
    Contact: "Contact"
  });

  function plannedEventsNamedOnly() {
    return PLANNED_EVENTS.ViewContent && PLANNED_EVENTS.Lead && PLANNED_EVENTS.Contact;
  }

  plannedEventsNamedOnly();

  var menuButton = document.querySelector(".menu-toggle");
  var panel = document.getElementById("mobile-nav");

  function setMenu(open, returnFocus) {
    if (!menuButton || !panel) return;
    menuButton.setAttribute("aria-expanded", open ? "true" : "false");
    menuButton.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    panel.hidden = !open;
    document.body.classList.toggle("menu-open", open);
    if (open) {
      var close = panel.querySelector("[data-close-menu]");
      if (close) close.focus();
    } else if (returnFocus !== false) {
      menuButton.focus();
    }
  }

  if (menuButton && panel) {
    menuButton.addEventListener("click", function () {
      setMenu(panel.hidden);
    });
    panel.addEventListener("click", function (event) {
      var target = event.target;
      if (!target || !target.closest) return;
      if (target.closest("[data-close-menu]")) setMenu(false, true);
      else if (target.closest("a")) setMenu(false, false);
    });
    document.addEventListener("keydown", function (event) {
      if (panel.hidden) return;
      if (event.key === "Escape") {
        setMenu(false);
        return;
      }
      if (event.key !== "Tab") return;
      var focusable = panel.querySelectorAll("a, button");
      if (!focusable.length) return;
      var first = focusable[0];
      var last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });
  }

  document.querySelectorAll(".nav-more").forEach(function (button) {
    button.addEventListener("click", function () {
      var open = button.getAttribute("aria-expanded") === "true";
      button.setAttribute("aria-expanded", open ? "false" : "true");
    });
  });

  var utmPattern = {
    source: /^(instagram|facebook|x|google|theknot|zola|max_[a-z0-9]+|team_[a-z0-9]+)$/,
    medium: /^(paid|organic|referral)$/,
    campaign: /^[a-z0-9]+_[a-z0-9]+$/,
    content: /^[A-Za-z0-9._-]{1,64}$/
  };

  function readUtm() {
    var params = new URLSearchParams(window.location.search);
    var stored = {};
    try {
      stored = JSON.parse(window.sessionStorage.getItem("jc-utm") || "{}") || {};
    } catch (error) {
      stored = {};
    }
    var next = {
      utm_source: stored.utm_source || "",
      utm_medium: stored.utm_medium || "",
      utm_campaign: stored.utm_campaign || "",
      utm_content: stored.utm_content || ""
    };
    ["source", "medium", "campaign", "content"].forEach(function (key) {
      var value = (params.get("utm_" + key) || "").trim();
      if (value && utmPattern[key].test(value)) next["utm_" + key] = value;
    });
    try {
      window.sessionStorage.setItem("jc-utm", JSON.stringify(next));
    } catch (error) {
      /* sessionStorage can be blocked; hidden fields still fill from the URL. */
    }
    return next;
  }

  function applyUtm(form) {
    var utm = readUtm();
    Object.keys(utm).forEach(function (key) {
      var field = form.querySelector('input[name="' + key + '"]');
      if (field) field.value = utm[key];
    });
  }

  function draftKey(form) {
    return "jc-draft-" + (form.getAttribute("id") || "form");
  }

  function saveDraft(form) {
    var data = {};
    form.querySelectorAll("input, select, textarea").forEach(function (field) {
      if (!field.name || field.type === "file" || field.name === "company_website") return;
      if (field.type === "checkbox") {
        data[field.name] = data[field.name] || [];
        if (field.checked) data[field.name].push(field.value);
        return;
      }
      if (field.type === "radio") {
        if (field.checked) data[field.name] = field.value;
        return;
      }
      data[field.name] = field.value;
    });
    try {
      window.sessionStorage.setItem(draftKey(form), JSON.stringify(data));
    } catch (error) {
      /* Keep the visible fields even if storage is unavailable. */
    }
  }

  function restoreDraft(form) {
    var raw = null;
    try {
      raw = window.sessionStorage.getItem(draftKey(form));
    } catch (error) {
      raw = null;
    }
    if (!raw) return;
    var data = {};
    try {
      data = JSON.parse(raw);
    } catch (error) {
      return;
    }
    form.querySelectorAll("input, select, textarea").forEach(function (field) {
      if (!field.name || field.type === "file" || !(field.name in data)) return;
      if (field.type === "checkbox") {
        var selected = data[field.name] || [];
        field.checked = selected.indexOf(field.value) !== -1;
        return;
      }
      if (field.type === "radio") {
        field.checked = data[field.name] === field.value;
        return;
      }
      if (typeof data[field.name] === "string") field.value = data[field.name];
    });
  }

  function setInvalid(field, message) {
    field.setAttribute("aria-invalid", "true");
    var error = field.closest(".form-row, .checks") && field.closest(".form-row, .checks").querySelector(".form-error");
    if (error) error.textContent = message;
  }

  function clearInvalid(form) {
    form.querySelectorAll("[aria-invalid]").forEach(function (field) {
      field.removeAttribute("aria-invalid");
    });
    form.querySelectorAll(".form-error").forEach(function (error) {
      error.textContent = "";
    });
  }

  function emailOk(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  }

  function validate(form) {
    clearInvalid(form);
    var messages = [];
    var requiredText = form.querySelectorAll("[data-required='text']");
    requiredText.forEach(function (field) {
      if (!field.value.trim()) {
        var label = field.getAttribute("data-label") || "This field";
        setInvalid(field, "Enter " + label + ".");
        messages.push(label);
      }
    });
    var email = form.querySelector("input[type='email']");
    if (email && email.value.trim() && !emailOk(email.value.trim())) {
      setInvalid(email, "Enter a valid email address.");
      messages.push("email");
    }
    form.querySelectorAll("[data-required='select']").forEach(function (field) {
      if (!field.value) {
        setInvalid(field, "Choose an option.");
        messages.push(field.name);
      }
    });
    form.querySelectorAll("[data-required='group']").forEach(function (group) {
      var any = group.querySelectorAll("input[type='checkbox']:checked").length > 0;
      if (!any) {
        var box = group.querySelector("input[type='checkbox']");
        if (box) setInvalid(box, "Select at least one.");
        var error = group.querySelector(".form-error");
        if (error) error.textContent = "Select at least one.";
        messages.push(group.getAttribute("data-label") || "selection");
      }
    });
    var consent = form.querySelector("input[name='consent']");
    if (consent && !consent.checked) {
      setInvalid(consent, "Confirm that we may email you about this request.");
      messages.push("consent");
    }
    var phone = form.querySelector("input[type='tel']");
    if (phone && phone.value.trim()) {
      var digits = phone.value.replace(/\D/g, "");
      if (digits.length < 7) {
        setInvalid(phone, "Check the phone number, or leave it blank.");
        messages.push("phone");
      }
    }
    var guests = form.querySelector("input[name='guest_count']");
    if (guests && guests.value.trim() && (!/^\d+$/.test(guests.value.trim()) || Number(guests.value) < 1)) {
      setInvalid(guests, "Enter a whole number, or leave this blank.");
      messages.push("guest count");
    }
    var quantity = form.querySelector("input[name='quantity']");
    if (quantity && (!/^\d+$/.test(quantity.value.trim()) || Number(quantity.value) < 1)) {
      setInvalid(quantity, "Enter a quantity of at least 1.");
      messages.push("quantity");
    }
    var files = form.querySelector("input[type='file']");
    if (files && files.files && files.files.length > 3) {
      setInvalid(files, "Choose up to 3 images. Files are not uploaded.");
      messages.push("files");
    } else if (files && files.files) {
      var maxBytes = 10 * 1024 * 1024;
      for (var i = 0; i < files.files.length; i++) {
        if (files.files[i].size > maxBytes) {
          setInvalid(files, "Each file must be 10 MB or smaller.");
          messages.push("files");
          break;
        }
      }
    }
    return messages;
  }

  document.querySelectorAll("form[data-review-form]").forEach(function (form) {
    applyUtm(form);
    restoreDraft(form);
    form.addEventListener("input", function () {
      saveDraft(form);
    });
    form.addEventListener("change", function () {
      saveDraft(form);
    });
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var button = form.querySelector("[type='submit']");
      if (button && button.disabled) return;
      if (button) {
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
      }
      var honeypot = form.querySelector("input[name='company_website']");
      var status = form.querySelector("#form-status");
      var problems = validate(form);
      if (honeypot && honeypot.value) {
        if (status) {
          status.textContent = "Nothing was sent. Please email info@joyfulcreationsli.com if you meant to write to the studio.";
        }
        if (button) {
          button.disabled = false;
          button.removeAttribute("aria-busy");
        }
        return;
      }
      if (problems.length) {
        if (status) {
          status.textContent = "The form still needs attention. Nothing was sent. Your entries stay on this page.";
        }
        var firstInvalid = form.querySelector("[aria-invalid='true']");
        if (firstInvalid) firstInvalid.focus();
        if (button) {
          button.disabled = false;
          button.removeAttribute("aria-busy");
        }
        return;
      }
      saveDraft(form);
      /* No endpoint. Do not call fetch, sendBeacon, or a mail client. */
      if (status) {
        status.textContent = "Nothing was sent. This review build has no form endpoint. Opening the thank-you wording.";
      }
      var next = form.getAttribute("data-thank-you");
      window.location.assign(next || "thank-you/");
    });
  });

  document.querySelectorAll("[data-filter-group]").forEach(function (group) {
    var buttons = group.querySelectorAll("[data-filter]");
    var items = group.querySelectorAll("[data-cat]");
    var empty = group.querySelector("[data-filter-empty]");
    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        var filter = button.getAttribute("data-filter");
        buttons.forEach(function (other) {
          other.setAttribute("aria-pressed", other === button ? "true" : "false");
        });
        var shown = 0;
        items.forEach(function (item) {
          var match = filter === "all" || item.getAttribute("data-cat") === filter;
          item.hidden = !match;
          if (match) shown += 1;
        });
        if (empty) empty.hidden = shown !== 0;
      });
    });
  });

  var reviewNote = document.getElementById("review-note");
  if (reviewNote && document.body.getAttribute("data-page") === "thank-you") {
    reviewNote.focus();
  }
})();
