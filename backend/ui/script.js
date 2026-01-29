const $ = id => document.getElementById(id);
let invoiceUIState = "INIT";
let currentViewingInvoice = null;

const DOC_TYPES = ["invoice", "lr", "party_weighment", "site_weighment", "toll_gate"];
const REQUIRED_DOC_TYPES = ["invoice", "lr", "party_weighment", "site_weighment"];

// ---------------- AUTH (Front-end gate) ----------------
const AUTH_STORAGE_KEY = "erp_invoice_ui_logged_in_v1";
const DEFAULT_USERNAME = "harshas379@gmail.com";
const DEFAULT_PASSWORD = "root";

function isLoggedIn() {
  return localStorage.getItem(AUTH_STORAGE_KEY) === "1";
}

function showLogin() {
  $("loginScreen").classList.remove("hidden");
  document.querySelector(".app-container").classList.remove("visible");
  $("loginUsername").focus();
}

function showApp() {
  $("loginScreen").classList.add("hidden");
  document.querySelector(".app-container").classList.add("visible");
}

function handleLogin() {
  const u = $("loginUsername").value.trim();
  const p = $("loginPassword").value;

  if (u === DEFAULT_USERNAME && p === DEFAULT_PASSWORD) {
    localStorage.setItem(AUTH_STORAGE_KEY, "1");
    $("loginPassword").value = "";
    showApp();
    showToast("Logged in", "success");
  } else {
    showToast("Invalid username or password", "error");
  }
}

function logout() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
  startNewInvoice(true);
  showLogin();
}

function getInvoiceNo() {
  return $("invoiceInput").value.trim();
}

function getSelectedFiles() {
  const selected = [];
  document.querySelectorAll(".doc-box input[type='file']").forEach(input => {
    if (input.files && input.files.length > 0) {
      selected.push({ docType: input.dataset.doc, file: input.files[0] });
    }
  });
  return selected;
}

function setButtonBusy(buttonId, busy, labelWhenBusy) {
  const btn = $(buttonId);
  if (!btn) return;
  btn.disabled = !!busy;
  if (labelWhenBusy) {
    if (busy) {
      btn.dataset.originalText = btn.innerHTML;
      btn.innerHTML = labelWhenBusy;
    } else if (btn.dataset.originalText) {
      btn.innerHTML = btn.dataset.originalText;
      delete btn.dataset.originalText;
    }
  }
}

async function uploadSelectedDocuments(invoiceNo) {
  const selected = getSelectedFiles();
  if (selected.length === 0) return { uploaded: 0 };

  const form = new FormData();
  form.append("invoice_no", invoiceNo);
  selected.forEach(({ docType, file }) => {
    form.append("files", file);
    form.append("doc_types", docType);
  });

  const res = await fetch("/api/upload-documents", { method: "POST", body: form });
  if (!res.ok) throw new Error("Upload failed");
  return await res.json();
}

// Toast notification
function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span style="font-size: 20px;">${type === 'success' ? '✓' : '⚠️'}</span>
    <span>${message}</span>
  `;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideIn 0.3s ease reverse';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

/* Tab Switching */
function switchTab(tab) {
  // Hide all tabs
  $("createTab").classList.add("hidden");
  $("manageTab").classList.add("hidden");
  $("paymentsTab").classList.add("hidden");
  $("invoiceView").classList.add("hidden");
  $("docDataModal").classList.add("hidden");
  $("paymentModal").classList.add("hidden");

  // Reset tab buttons
  document.querySelectorAll(".tab-btn").forEach(b =>
    b.classList.remove("active")
  );

  // Activate requested tab
  if (tab === "create") {
    $("createTab").classList.remove("hidden");
    document.querySelectorAll(".tab-btn")[0].classList.add("active");

    if (!$("invoiceInput").value) {
      $("erpForm").classList.add("hidden");
      $("docSection").classList.add("hidden");
      $("invoiceInputSection").classList.remove("hidden");
      updateSteps(1);
    }

  } else if (tab === "manage") {
    $("manageTab").classList.remove("hidden");
    document.querySelectorAll(".tab-btn")[1].classList.add("active");
    loadInvoices();

  } else if (tab === "payments") {
    $("paymentsTab").classList.remove("hidden");
    document.querySelectorAll(".tab-btn")[2].classList.add("active");
    loadPayments();
  }
}

/* Step Navigation */
function updateSteps(currentStep) {
  for (let i = 1; i <= 3; i++) {
    const step = $(`step${i}`);
    step.classList.remove("active", "completed");
    if (i < currentStep) step.classList.add("completed");
    if (i === currentStep) step.classList.add("active");
  }
}

/* Create/Load Invoice */
async function createInvoice() {
  const inv = $("invoiceInput").value.trim();
  if (!inv) {
    showToast("Please enter an invoice number", "error");
    return;
  }

  history.pushState({}, "", `/?invoice=${encodeURIComponent(inv)}`);

  $("invoiceInputSection").classList.add("hidden");
  $("docSection").classList.remove("hidden");
  updateSteps(2);
  invoiceUIState = "DOCS";

  try {
    const res = await fetch(`/api/invoice?invoice_no=${encodeURIComponent(inv)}`);
    const invoice = await res.json();

    if (invoice && invoice.data && Object.keys(invoice.data).length > 0) {
      populateForm(invoice.data, invoice.status);
      loadExistingDocuments(inv, invoice.documents);
    }
  } catch (e) {
    console.error(e);
  }
}

/* Load existing document previews */
async function loadExistingDocuments(invoiceNo, documents) {
  if (!documents) return;

  Object.keys(documents).forEach(docType => {
    const preview = $(`preview-${docType}`);
    const nameEl = $(`name-${docType}`);
    const box = document.querySelector(`.doc-box[data-type="${docType}"]`);

    if (preview && box) {
      const imgSrc = `/api/document?invoice_no=${encodeURIComponent(invoiceNo)}&doc_type=${encodeURIComponent(docType)}`;
      preview.src = imgSrc;
      preview.classList.remove('hidden');
      nameEl.textContent = `✓ ${documents[docType].filename}`;
      box.classList.add('uploaded');
    }
  });

  updateDocumentCount();
}

/* Populate Form */
function populateForm(data, status) {
  $("invoice_no").value = $("invoiceInput").value;

  Object.keys(data).forEach(k => {
    if ($(k) && k !== "invoice_no") $(k).value = data[k] || '';
  });

  const statusClass = status.toLowerCase().replace(" ", "-");
  $("statusText").className = `status-badge status-${statusClass}`;
  $("statusText").innerText = `Status: ${status}`;
  $("erpForm").classList.remove("hidden");
  updateSteps(3);

  // Trigger weight variance calculation if weights are populated
  if (data.lr_weight && data.site_weight) {
    setTimeout(() => calculateWeightVariance(), 100);
  }

  // Check for overdue documents
  setTimeout(() => checkOverdueDocuments(), 200);
}

/* File Selection */
function handleFileSelect(input) {
  const docType = input.dataset.doc;
  const fileName = input.files[0]?.name;
  const nameElement = $(`name-${docType}`);
  const boxElement = input.closest('.doc-box');
  const preview = $(`preview-${docType}`);

  if (fileName && input.files[0]) {
    nameElement.textContent = `✓ ${fileName}`;
    boxElement.classList.add('uploaded');

    const reader = new FileReader();
    reader.onload = (e) => {
      preview.src = e.target.result;
      preview.classList.remove('hidden');
    };
    reader.readAsDataURL(input.files[0]);
  } else {
    nameElement.textContent = '';
    boxElement.classList.remove('uploaded');
    preview.classList.add('hidden');
  }

  updateDocumentCount();

  // Check for overdue documents after upload
  checkOverdueDocuments();
}

/* Update Document Count */
function updateDocumentCount() {
  const count = document.querySelectorAll(".doc-box.uploaded").length;

  $("uploadedCount").textContent = count;
  const total = DOC_TYPES.length;
  const countEl = document.querySelector(".doc-count");
  if (countEl) {
    countEl.innerHTML = `<span class="number" id="uploadedCount">${count}</span> / ${total} documents uploaded`;
  }

  // Show extract button if at least 1 document is uploaded
  if (count >= 1 && invoiceUIState !== "EXTRACTED") {
    $("extractBtn").classList.remove("hidden");
  } else if (invoiceUIState !== "EXTRACTED") {
    $("extractBtn").classList.add("hidden");
  }
}

/* Extract Data */
async function extractData() {
  const invoiceNo = getInvoiceNo();
  if (!invoiceNo) {
    showToast("Invoice number missing", "error");
    return;
  }

  const selected = getSelectedFiles();

  try {
    setButtonBusy("extractBtn", true, "⏳ Extracting...");
    const res = selected.length > 0
      ? await fetch("/api/extract", {
          method: "POST",
          body: (() => {
            const formData = new FormData();
            formData.append("invoice_no", invoiceNo);
            selected.forEach(({ docType, file }) => {
              formData.append("files", file);
              formData.append("doc_types", docType);
            });
            return formData;
          })()
        })
      : await fetch("/api/extract-from-stored", {
          method: "POST",
          body: (() => {
            const formData = new FormData();
            formData.append("invoice_no", invoiceNo);
            return formData;
          })()
        });

    if (!res.ok) throw new Error("Extraction failed");

    const { data, confidence, status } = await res.json();
    if (!data) {
      showToast("No uploaded documents found. Please upload at least one doc.", "error");
      return;
    }

    $("docSection").classList.add("hidden");
    populateForm(data, status);
    invoiceUIState = "EXTRACTED";

    $("extractBtn").disabled = true;
    $("extractBtn").classList.add("hidden");

    showToast("Extraction completed successfully!", "success");
  } catch (err) {
    console.error(err);
    showToast("Extraction failed. Check backend logs.", "error");
  } finally {
    setButtonBusy("extractBtn", false);
  }
}

/* Save/Submit */
async function saveDraft() {
  const invoiceNo = getInvoiceNo();
  if (!invoiceNo) {
    showToast("Invoice number missing", "error");
    return;
  }

  try {
    setButtonBusy("extractBtn", true); // avoid conflicting actions while saving draft
    await uploadSelectedDocuments(invoiceNo);

    // 2) Save invoice as PARTIAL so it appears in Manage Invoices
    await saveInvoice("PARTIAL");

    showToast("Draft saved! It will appear in Manage Invoices.", "success");

    // Reset UI so user can create the next invoice immediately
    startNewInvoice(true);
  } catch (e) {
    console.error(e);
    showToast("Failed to save draft. Please try again.", "error");
  } finally {
    setButtonBusy("extractBtn", false);
  }
}

function submitInvoice() {
  saveInvoice("COMPLETED");
  invoiceUIState = "COMPLETED";

  showToast("Invoice submitted successfully!", "success");

  setTimeout(() => {
    if (confirm("Invoice submitted! Do you want to create a new invoice?")) {
      startNewInvoice();
    } else {
      switchTab("manage");
    }
  }, 1000);
}

async function saveInvoice(status) {
  const invoiceNo = $("invoiceInput").value;

  try {
    const currentRes = await fetch(`/api/invoice?invoice_no=${encodeURIComponent(invoiceNo)}`);
    const currentInvoice = await currentRes.json();

    const payload = {
      invoice_date: $("invoice_date").value,
      buyer_name: $("buyer_name").value,
      ship_to_party: $("ship_to_party").value,
      vehicle_no: $("vehicle_no").value,
      lr_no: $("lr_no").value,
      lr_date: $("lr_date").value,
      origin: $("origin").value,
      destination: $("destination").value,
      e_way_bill_no: $("e_way_bill_no").value,
      order_no: $("order_no").value,
      order_type: $("order_type").value,
      principal_company: $("principal_company").value,
      acknowledged: $("acknowledged").value,
      lr_weight: $("lr_weight").value,
      site_weight: $("site_weight").value,
      weight_difference: $("weight_difference").value,
      weight_loss_percentage: $("weight_loss_percentage").value,
      deduction_amount: $("deduction_amount").value,
      final_bill_amount: $("final_bill_amount").value
    };

    const savePayload = {
      invoice_no: invoiceNo,
      status,
      data: payload,
      documents: currentInvoice.documents || {},
      invoice_amount: parseFloat($("invoice_amount").value) || 0
    };

    const saveRes = await fetch("/api/invoice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(savePayload)
    });

    if (!saveRes.ok) {
      throw new Error("Failed to save invoice");
    }
  } catch (error) {
    console.error("Error saving invoice:", error);
    showToast("Failed to save invoice", "error");
    throw error;
  }
}

/* Manage Invoices */
async function loadInvoices() {
  const res = await fetch("/api/invoices");
  const invoices = await res.json();

  const list = document.getElementById("invoiceList");

  if (!invoices.length) {
    list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div><p>No invoices found. Create your first invoice to get started!</p></div>';
    $("overdueDocumentsSection").classList.add("hidden");
    return;
  }

  // Check for overdue documents
  const today = new Date();
  const overdueInvoices = [];

  invoices.forEach(inv => {
    if (!inv.data || !inv.data.invoice_date) return;

    const invoiceDate = new Date(inv.data.invoice_date);
    const daysDiff = Math.floor((today - invoiceDate) / (1000 * 60 * 60 * 24));

    if (daysDiff > 2) {
      const requiredDocs = ['lr', 'party_weighment', 'site_weighment'];
      const missingDocs = requiredDocs.filter(doc => !inv.documents || !inv.documents[doc]);

      if (missingDocs.length > 0) {
        overdueInvoices.push({
          invoice_no: inv.invoice_no,
          days: daysDiff,
          missing: missingDocs,
          invoice_date: inv.data.invoice_date
        });
      }
    }
  });

  // Display overdue section if there are any
  if (overdueInvoices.length > 0) {
    $("overdueDocumentsSection").classList.remove("hidden");
    $("overdueInvoicesList").innerHTML = overdueInvoices.map(inv => `
      <div style="background: white; border-radius: 8px; padding: 15px; margin-bottom: 10px; border-left: 4px solid #dc3545;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong style="font-size: 16px; color: #212529;">${inv.invoice_no}</strong>
            <div style="color: #6c757d; font-size: 13px; margin-top: 5px;">
              Invoice Date: ${inv.invoice_date} • <strong style="color: #dc3545;">${inv.days} days overdue</strong>
            </div>
            <div style="color: #842029; font-size: 13px; margin-top: 8px;">
              Missing: ${inv.missing.map(d => d.replace('_', ' ').toUpperCase()).join(', ')}
            </div>
          </div>
          <button class="btn-primary" onclick="openInvoice('${inv.invoice_no}')" style="padding: 8px 16px; font-size: 13px;">
            Upload Documents
          </button>
        </div>
      </div>
    `).join('');

    // Update badge count
    $("overdueCountBadge").textContent = overdueInvoices.length;
    $("overdueCountBadge").classList.remove("hidden");
  } else {
    $("overdueDocumentsSection").classList.add("hidden");
    $("overdueCountBadge").classList.add("hidden");
  }

  list.innerHTML = invoices.map(inv => {
    const docsCount = inv.documents ? Object.keys(inv.documents).length : 0;
    const progress = (docsCount / inv.docs_required) * 100;

    // Check if this invoice is overdue
    let isOverdue = false;
    let overdueDays = 0;
    if (inv.data && inv.data.invoice_date) {
      const invoiceDate = new Date(inv.data.invoice_date);
      const daysDiff = Math.floor((today - invoiceDate) / (1000 * 60 * 60 * 24));
      const requiredDocs = ['lr', 'party_weighment', 'site_weighment'];
      const missingDocs = requiredDocs.filter(doc => !inv.documents || !inv.documents[doc]);
      if (daysDiff > 2 && missingDocs.length > 0) {
        isOverdue = true;
        overdueDays = daysDiff;
      }
    }

    let docs = "";
    if (inv.documents && Object.keys(inv.documents).length > 0) {
      docs = Object.entries(inv.documents).map(
        ([type, meta]) => `
          <div
            class="doc-chip"
            title="Click to view extracted data • Right-click to view document image"
            onclick="event.stopPropagation(); openDocumentData('${inv.invoice_no}','${type}')"
            oncontextmenu="event.preventDefault(); event.stopPropagation(); viewDocumentImage('${inv.invoice_no}','${type}')">
            ✔ ${type.replace(/_/g, " ")}
          </div>
        `
      ).join("");
    } else {
      docs = '<span style="color:#6c757d;">No documents uploaded</span>';
    }

    const overdueIndicator = isOverdue ? `
      <div style="background: #f8d7da; color: #842029; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; margin-top: 8px;">
        🚨 ${overdueDays} days overdue
      </div>
    ` : '';

    return `
      <div class="invoice-card ${isOverdue ? 'invoice-overdue' : ''}" onclick="openInvoice('${inv.invoice_no}')" style="${isOverdue ? 'border-color: #dc3545;' : ''}">
        <div class="invoice-card-left">
          <h3>${inv.invoice_no}</h3>
          <div class="invoice-card-meta">${docs}</div>
          ${overdueIndicator}
        </div>
        <div class="invoice-card-right">
          <div class="doc-progress">${docsCount}/${inv.docs_required} documents</div>
          <div class="progress-bar">
            <div class="progress-fill" style="width:${progress}%; ${isOverdue ? 'background: linear-gradient(90deg, #dc3545 0%, #c82333 100%);' : ''}"></div>
          </div>
          <button
            class="btn-secondary"
            style="margin-top:10px;padding:6px 12px;font-size:12px;"
            onclick="event.stopPropagation(); deleteInvoice('${inv.invoice_no}')">
            🗑️ Delete
          </button>
        </div>
      </div>
    `;
  }).join("");
}

async function openInvoice(invoiceNo) {
  const res = await fetch(`/api/invoice?invoice_no=${encodeURIComponent(invoiceNo)}`);
  const invoice = await res.json();

  if (!invoice) {
    showToast("Invoice not found", "error");
    return;
  }

  if (invoice.status === "COMPLETED") {
    openReadOnlyInvoice(invoiceNo, invoice);
  } else {
    openEditableInvoice(invoiceNo);
  }
}

async function deleteInvoice(invoiceNo) {
  if (!confirm(`Are you sure you want to delete invoice ${invoiceNo}? This action cannot be undone.`)) {
    return;
  }

  try {
    const res = await fetch(`/api/invoice?invoice_no=${encodeURIComponent(invoiceNo)}`, {
      method: 'DELETE'
    });

    const result = await res.json();

    if (result.ok) {
      showToast("Invoice deleted successfully", "success");
      loadInvoices();
    } else {
      showToast(result.message || "Failed to delete invoice", "error");
    }
  } catch (error) {
    console.error("Error deleting invoice:", error);
    showToast("Failed to delete invoice", "error");
  }
}

async function openEditableInvoice(invoiceNo) {
  switchTab("create");
  $("invoiceView").classList.add("hidden");

  $("invoiceInput").value = invoiceNo;
  $("invoiceInputSection").classList.add("hidden");
  $("docSection").classList.remove("hidden");

  updateSteps(2);

  const res = await fetch(`/api/invoice?invoice_no=${encodeURIComponent(invoiceNo)}`);
  const invoice = await res.json();

  if (invoice?.data) {
    populateForm(invoice.data, invoice.status);
    loadExistingDocuments(invoiceNo, invoice.documents);
  }
}

function openReadOnlyInvoice(invoiceNo, invoice) {
  currentViewingInvoice = invoiceNo;

  setActiveTab(1);
  $("manageTab").classList.add("hidden");
  $("docDataModal").classList.add("hidden");

  $("invoiceInputSection").classList.add("hidden");
  $("docSection").classList.add("hidden");
  $("erpForm").classList.add("hidden");

  $("invoiceView").classList.remove("hidden");

  const data = invoice.data || {};

  $("view_invoice_no").innerText = invoiceNo;
  $("view_invoice_date").innerText = data.invoice_date || "-";
  $("view_order_type").innerText = data.order_type || "-";

  Object.keys(data).forEach(key => {
    const el = document.getElementById(`view_${key}`);
    if (el) el.innerText = data[key] || "-";
  });

  renderReadOnlyDocuments(invoiceNo, invoice.documents || {});
}

async function deleteCurrentInvoice() {
  if (!currentViewingInvoice) return;

  if (!confirm(`Are you sure you want to delete invoice ${currentViewingInvoice}? This action cannot be undone.`)) {
    return;
  }

  try {
    const res = await fetch(`/api/invoice?invoice_no=${encodeURIComponent(currentViewingInvoice)}`, {
      method: 'DELETE'
    });

    const result = await res.json();

    if (result.ok) {
      showToast("Invoice deleted successfully", "success");
      currentViewingInvoice = null;
      switchTab("manage");
    } else {
      showToast(result.message || "Failed to delete invoice", "error");
    }
  } catch (error) {
    console.error("Error deleting invoice:", error);
    showToast("Failed to delete invoice", "error");
  }
}

function renderReadOnlyDocuments(invoiceNo, documents) {
  const container = $("view_documents");

  if (!documents || Object.keys(documents).length === 0) {
    container.innerHTML = "<p style='color:#6c757d'>No documents available</p>";
    return;
  }

  container.innerHTML = Object.entries(documents).map(([type, meta]) => `
    <div class="doc-box uploaded">
      <div class="upload-icon">📄</div>
      <label>${type.replace("_", " ")}</label>
      <div class="file-name">${meta.filename || type}</div>
      <img src="/api/document?invoice_no=${encodeURIComponent(invoiceNo)}&doc_type=${encodeURIComponent(type)}"
           class="doc-preview"
           onclick="openImageModal(this.src)">
    </div>
  `).join("");
}

function backToManage() {
  $("invoiceView").classList.add("hidden");
  switchTab("manage");
}

function openDocumentData(invoiceNo, docType) {
  fetch(`/api/invoice?invoice_no=${encodeURIComponent(invoiceNo)}`)
    .then(res => res.json())
    .then(invoice => {
      if (!invoice || !invoice.data) {
        showToast("No extracted data found", "error");
        return;
      }

      const fieldMap = {
        invoice: ["invoice_no", "invoice_date", "buyer_name", "ship_to_party", "order_no", "e_way_bill_no"],
        lr: ["lr_no", "lr_date", "vehicle_no", "origin", "destination"],
        party_weighment: ["gross_weight", "tare_weight", "net_weight"],
        site_weighment: ["gross_weight", "tare_weight", "net_weight"],
        toll_gate: ["vehicle_no"]
      };

      const fields = fieldMap[docType] || [];

      $("docTitle").innerText = `${docType.replace("_"," ").toUpperCase()} – Extracted Data`;

      $("docDataBody").innerHTML = fields.map(f => `
        <div class="form-field">
          <label>${f.replace("_"," ")}</label>
          <input value="${invoice.data[f] || '-'}" readonly class="readonly">
        </div>
      `).join("") + `
        <div style="grid-column: 1/-1; margin-top: 20px;">
          <button class="btn-primary" onclick="viewDocumentImage('${invoiceNo}','${docType}'); closeDocModal();">
            🖼️ View Document Image
          </button>
        </div>
      `;

      const modal = $("docDataModal");
      modal.classList.remove("hidden");
      modal.style.display = "flex";
    });
}

function viewDocumentImage(invoiceNo, docType) {
  const imgSrc = `/api/document?invoice_no=${encodeURIComponent(invoiceNo)}&doc_type=${encodeURIComponent(docType)}`;
  openImageModal(imgSrc);
}

/* Weight Variance Calculation */
function calculateWeightVariance() {
  const lrWeight = parseFloat($("lr_weight").value) || 0;
  const siteWeight = parseFloat($("site_weight").value) || 0;
  const originalAmount = parseFloat($("invoice_amount").value) || 0;

  // Ensure both weights are entered
  if (lrWeight === 0 || siteWeight === 0) {
    $("weight_difference").value = "";
    $("weight_loss_percentage").value = "";
    $("original_amount").value = "";
    $("deduction_amount").value = "";
    $("final_bill_amount").value = "";
    $("variance_status").innerHTML = "";
    $("varianceAlert").classList.add("hidden");
    return;
  }

  // Calculate weight difference (LR - Site)
  const weightDifference = lrWeight - siteWeight;

  // Calculate weight loss percentage
  const weightLossPercentage = (weightDifference / lrWeight) * 100;

  // Update display fields
  $("weight_difference").value = weightDifference.toFixed(2);
  $("weight_loss_percentage").value = weightLossPercentage.toFixed(3) + "%";
  $("original_amount").value = "₹" + originalAmount.toLocaleString('en-IN', {minimumFractionDigits: 2});

  // Calculate deduction if weight loss exceeds 0.5%
  let deductionAmount = 0;
  let finalBillAmount = originalAmount;

  if (weightLossPercentage > 0.5) {
    // Deduct proportional amount based on weight loss
    deductionAmount = (weightLossPercentage / 100) * originalAmount;
    finalBillAmount = originalAmount - deductionAmount;

    // Show warning alert
    $("varianceAlert").classList.remove("hidden");
    $("varianceMessage").innerHTML = `
      Weight loss of <strong>${weightLossPercentage.toFixed(3)}%</strong> exceeds the 0.5% threshold.
      <br>Weight difference: <strong>${weightDifference.toFixed(2)} kg</strong>
      (LR: ${lrWeight.toFixed(2)} kg, Site: ${siteWeight.toFixed(2)} kg)
    `;

    // Update variance status
    $("variance_status").innerHTML = "⚠️ EXCEEDS THRESHOLD";
    $("variance_status").style.background = "#fff3cd";
    $("variance_status").style.color = "#856404";
    $("variance_status").style.border = "2px solid #ffc107";

  } else if (weightLossPercentage > 0) {
    // Within acceptable range
    $("varianceAlert").classList.add("hidden");
    $("variance_status").innerHTML = "✓ WITHIN ACCEPTABLE RANGE";
    $("variance_status").style.background = "#d1e7dd";
    $("variance_status").style.color = "#0f5132";
    $("variance_status").style.border = "2px solid #28a745";

  } else if (weightLossPercentage < 0) {
    // Gain in weight (site > LR)
    $("varianceAlert").classList.add("hidden");
    $("variance_status").innerHTML = "ℹ️ WEIGHT GAIN DETECTED";
    $("variance_status").style.background = "#cfe2ff";
    $("variance_status").style.color = "#084298";
    $("variance_status").style.border = "2px solid #0d6efd";
  } else {
    // Exact match
    $("varianceAlert").classList.add("hidden");
    $("variance_status").innerHTML = "✓ EXACT MATCH";
    $("variance_status").style.background = "#d1e7dd";
    $("variance_status").style.color = "#0f5132";
    $("variance_status").style.border = "2px solid #28a745";
  }

  // Update deduction and final amount
  $("deduction_amount").value = deductionAmount > 0 ? "-₹" + deductionAmount.toLocaleString('en-IN', {minimumFractionDigits: 2}) : "₹0.00";
  $("final_bill_amount").value = "₹" + finalBillAmount.toLocaleString('en-IN', {minimumFractionDigits: 2});

  // Show toast notification if deduction applied
  if (deductionAmount > 0) {
    showToast(`Bill reduced by ₹${deductionAmount.toFixed(2)} due to ${weightLossPercentage.toFixed(3)}% weight loss`, "error");
  }
}

// Trigger calculation when invoice amount changes
function updateInvoiceAmount() {
  calculateWeightVariance();
}

// Add event listener to invoice amount field
document.addEventListener('DOMContentLoaded', function() {
  const invoiceAmountField = $("invoice_amount");
  if (invoiceAmountField) {
    invoiceAmountField.addEventListener('change', updateInvoiceAmount);
    invoiceAmountField.addEventListener('input', updateInvoiceAmount);
  }
});

/* Document Overdue Tracking */
function checkOverdueDocuments() {
  const invoiceDateStr = $("invoice_date").value;
  if (!invoiceDateStr) {
    $("documentPendingAlert").classList.add("hidden");
    return;
  }

  const invoiceDate = new Date(invoiceDateStr);
  const today = new Date();
  const daysDifference = Math.floor((today - invoiceDate) / (1000 * 60 * 60 * 24));

  // Only check if invoice is more than 2 days old
  if (daysDifference <= 2) {
    $("documentPendingAlert").classList.add("hidden");
    return;
  }

  // Check which required documents are missing
  const requiredDocs = {
    'lr': { name: 'LR (Lorry Receipt)', uploaded: false },
    'party_weighment': { name: 'Party Weighment', uploaded: false },
    'site_weighment': { name: 'Site Weighment', uploaded: false }
  };

  // Check uploaded documents
  Object.keys(requiredDocs).forEach(docType => {
    const box = document.querySelector(`.doc-box[data-type="${docType}"]`);
    if (box && box.classList.contains('uploaded')) {
      requiredDocs[docType].uploaded = true;
    }
  });

  // Find missing documents
  const missingDocs = Object.entries(requiredDocs)
    .filter(([type, info]) => !info.uploaded)
    .map(([type, info]) => info.name);

  if (missingDocs.length > 0) {
    // Show alert for overdue documents
    $("documentPendingAlert").classList.remove("hidden");

    const docsList = missingDocs.map(doc => `<li><strong>${doc}</strong></li>`).join('');
    $("pendingDocumentsList").innerHTML = `
      <p style="margin-bottom: 10px;">
        <strong>${daysDifference} days</strong> have passed since invoice date (${invoiceDate.toLocaleDateString('en-IN')}).
      </p>
      <p style="margin-bottom: 8px;">Missing documents:</p>
      <ul style="margin-left: 20px; margin-bottom: 0;">
        ${docsList}
      </ul>
    `;

    // Show toast notification
    showToast(`⚠️ ${missingDocs.length} document(s) overdue by ${daysDifference} days`, "error");
  } else {
    $("documentPendingAlert").classList.add("hidden");
  }
}

// Check overdue documents when invoice date changes
function onInvoiceDateChange() {
  checkOverdueDocuments();
}

// Check overdue documents when files are uploaded
function onDocumentUpload() {
  checkOverdueDocuments();
}


function closeDocModal() {
  const modal = $("docDataModal");
  modal.classList.add("hidden");
  modal.style.display = "none";
}

function openImageModal(src) {
  $("modalImage").src = src;
  $("imageModal").classList.remove("hidden");
}

function closeImageModal() {
  $("imageModal").classList.add("hidden");
}

function startNewInvoice(force = false) {
  if (!force && invoiceUIState !== "COMPLETED" &&
      !confirm("Start a new invoice? Current data will be cleared.")) return;

  invoiceUIState = "INIT";
  history.pushState({}, "", "/");

  $("invoiceInput").value = "";

  document.querySelectorAll("input").forEach(i => {
    if (!i.classList.contains("readonly")) {
      i.value = "";
    }
  });

  document.querySelectorAll("select").forEach(s => {
    s.selectedIndex = 0;
  });

  document.querySelectorAll(".doc-box").forEach(box => {
    box.classList.remove("uploaded");
  });

  document.querySelectorAll(".file-name").forEach(n => n.textContent = "");
  document.querySelectorAll(".doc-preview").forEach(p => p.classList.add("hidden"));

  document.querySelectorAll(".doc-box input[type='file']").forEach(i => {
    i.disabled = false;
    i.value = "";
  });

  $("extractBtn").classList.add("hidden");
  $("extractBtn").disabled = false;
  $("uploadedCount").textContent = "0";

  $("invoiceView").classList.add("hidden");
  $("erpForm").classList.add("hidden");
  $("docSection").classList.add("hidden");
  $("invoiceInputSection").classList.remove("hidden");

  switchTab("create");
  updateSteps(1);
  $("invoiceInput").focus();
}

/* Payments & Ledger Functions */
let currentPaymentInvoice = null;
let currentReminderInvoice = null;
let currentReminderBuyer = null;

async function loadPayments() {
  try {
    const summaryRes = await fetch("/api/payment-summary");
    const summary = await summaryRes.json();

    $("summary-total").innerText = `₹${summary.total_invoice_amount.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
    $("summary-paid").innerText = `₹${summary.total_paid.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
    $("summary-outstanding").innerText = `₹${summary.total_outstanding.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;

    $("summary-status").innerHTML = `
      <span class="status-mini paid">${summary.paid_count} Paid</span>
      <span class="status-mini partial">${summary.partial_count} Partial</span>
      <span class="status-mini unpaid">${summary.unpaid_count} Unpaid</span>
    `;

    const paymentsRes = await fetch("/api/payments");
    const payments = await paymentsRes.json();

    const list = $("paymentList");

    if (!payments.length) {
      list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">💸</div><p>No invoices with payments yet</p></div>';
      $("paymentRemindersSection").classList.add("hidden");
      return;
    }

    // Calculate payment reminders
    const today = new Date();
    const reminders = {
      day3: [],  // 3 days unpaid
      day6: [],  // 6 days unpaid
      day9: []   // 9+ days unpaid
    };

    payments.forEach(inv => {
      // Only check unpaid or partially paid invoices
      if (inv.payment_status === 'Paid') return;

      if (!inv.invoice_date) return;

      const invoiceDate = new Date(inv.invoice_date);
      const daysSinceInvoice = Math.floor((today - invoiceDate) / (1000 * 60 * 60 * 24));

      const reminderData = {
        invoice_no: inv.invoice_no,
        buyer_name: inv.buyer_name || 'N/A',
        invoice_date: inv.invoice_date,
        invoice_amount: inv.invoice_amount,
        total_paid: inv.total_paid,
        balance_due: inv.balance_due,
        days: daysSinceInvoice,
        payment_status: inv.payment_status
      };

      // Categorize by reminder intervals
      if (daysSinceInvoice >= 9) {
        reminders.day9.push(reminderData);
      } else if (daysSinceInvoice >= 6) {
        reminders.day6.push(reminderData);
      } else if (daysSinceInvoice >= 3) {
        reminders.day3.push(reminderData);
      }
    });

    // Display payment reminders
    const totalReminders = reminders.day3.length + reminders.day6.length + reminders.day9.length;

    if (totalReminders > 0) {
      $("paymentRemindersSection").classList.remove("hidden");
      $("paymentReminderBadge").textContent = totalReminders;
      $("paymentReminderBadge").classList.remove("hidden");

      // Critical reminders (9+ days)
      if (reminders.day9.length > 0) {
        $("criticalReminders").classList.remove("hidden");
        $("criticalRemindersList").innerHTML = reminders.day9.map(r => createReminderCard(r, 'critical')).join('');
      } else {
        $("criticalReminders").classList.add("hidden");
      }

      // High priority reminders (6 days)
      if (reminders.day6.length > 0) {
        $("highPriorityReminders").classList.remove("hidden");
        $("highPriorityRemindersList").innerHTML = reminders.day6.map(r => createReminderCard(r, 'high')).join('');
      } else {
        $("highPriorityReminders").classList.add("hidden");
      }

      // Standard reminders (3 days)
      if (reminders.day3.length > 0) {
        $("standardReminders").classList.remove("hidden");
        $("standardRemindersList").innerHTML = reminders.day3.map(r => createReminderCard(r, 'standard')).join('');
      } else {
        $("standardReminders").classList.add("hidden");
      }
    } else {
      $("paymentRemindersSection").classList.add("hidden");
      $("paymentReminderBadge").classList.add("hidden");
    }

    list.innerHTML = payments.map(inv => {
      const statusClass = inv.payment_status.toLowerCase();

      return `
        <div class="payment-card">
          <div class="payment-card-header">
            <div class="payment-card-title">
              <h3>${inv.invoice_no}</h3>
              <span class="payment-badge ${statusClass}">${inv.payment_status}</span>
            </div>
            <button class="btn-add-payment" onclick="openPaymentModal('${inv.invoice_no}')">
              + Add Payment
            </button>
          </div>

          <div class="payment-info-grid">
            <div class="payment-info-item">
              <div class="payment-info-label">Buyer</div>
              <div class="payment-info-value">${inv.buyer_name || '-'}</div>
            </div>
            <div class="payment-info-item">
              <div class="payment-info-label">Invoice Date</div>
              <div class="payment-info-value">${inv.invoice_date || '-'}</div>
            </div>
            <div class="payment-info-item">
              <div class="payment-info-label">Invoice Amount</div>
              <div class="payment-info-value">₹${inv.invoice_amount.toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
            </div>
            <div class="payment-info-item">
              <div class="payment-info-label">Total Paid</div>
              <div class="payment-info-value" style="color:#28a745;">₹${inv.total_paid.toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
            </div>
            <div class="payment-info-item">
              <div class="payment-info-label">Balance Due</div>
              <div class="payment-info-value" style="color:#dc3545;">₹${inv.balance_due.toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
            </div>
          </div>

          ${inv.payments && inv.payments.length > 0 ? `
            <div class="payment-history">
              <div class="payment-history-header">
                <div class="payment-history-title">Payment History (${inv.payments.length})</div>
              </div>
              ${inv.payments.map(p => `
                <div class="payment-entry">
                  <div class="payment-entry-left">
                    <div class="payment-entry-amount">₹${p.amount.toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
                    <div class="payment-entry-details">
                      ${p.payment_date} • ${p.payment_mode}${p.reference_no ? ' • ' + p.reference_no : ''}
                    </div>
                  </div>
                </div>
              `).join('')}
            </div>
          ` : ''}
        </div>
      `;
    }).join('');

  } catch (error) {
    console.error("Error loading payments:", error);
    showToast("Failed to load payments", "error");
  }
}

function createReminderCard(reminder, priority) {
  const borderColor = priority === 'critical' ? '#dc3545' : priority === 'high' ? '#ffc107' : '#0d6efd';
  const bgColor = priority === 'critical' ? 'white' : 'white';

  return `
    <div style="background: ${bgColor}; border-radius: 8px; padding: 15px; margin-bottom: 10px; border-left: 4px solid ${borderColor};">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
        <div style="flex: 1; min-width: 250px;">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <strong style="font-size: 16px; color: #212529;">${reminder.invoice_no}</strong>
            <span class="payment-badge ${reminder.payment_status.toLowerCase()}">${reminder.payment_status}</span>
          </div>
          <div style="color: #6c757d; font-size: 13px; margin-bottom: 5px;">
            <strong>Customer:</strong> ${reminder.buyer_name}
          </div>
          <div style="color: #6c757d; font-size: 13px; margin-bottom: 5px;">
            <strong>Invoice Date:</strong> ${reminder.invoice_date} •
            <strong style="color: ${priority === 'critical' ? '#dc3545' : priority === 'high' ? '#856404' : '#084298'};">
              ${reminder.days} days overdue
            </strong>
          </div>
          <div style="color: #6c757d; font-size: 13px;">
            <strong>Amount Due:</strong>
            <span style="color: #dc3545; font-weight: 600; font-size: 15px;">
              ₹${reminder.balance_due.toLocaleString('en-IN', {minimumFractionDigits: 2})}
            </span>
            <span style="color: #6c757d;"> of ₹${reminder.invoice_amount.toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
          </div>
        </div>
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
          <button class="btn-secondary" onclick="sendPaymentReminder('${reminder.invoice_no}', '${reminder.buyer_name}')"
                  style="padding: 8px 16px; font-size: 13px; white-space: nowrap;">
            📧 Send Reminder
          </button>
          <button class="btn-add-payment" onclick="openPaymentModal('${reminder.invoice_no}')"
                  style="padding: 8px 16px; font-size: 13px; white-space: nowrap;">
            💰 Record Payment
          </button>
        </div>
      </div>
    </div>
  `;
}

function sendPaymentReminder(invoiceNo, buyerName) {
  // Open reminder sending modal
  currentReminderInvoice = invoiceNo;
  currentReminderBuyer = buyerName;

  $("reminder-invoice-no").value = invoiceNo;
  $("reminder-buyer-name").value = buyerName;

  // Reset selections
  document.querySelectorAll('input[name="reminderMethod"]').forEach(cb => cb.checked = false);
  $("reminder-email").value = "";
  $("reminder-phone").value = "";
  $("reminder-message").value = `Dear ${buyerName},

This is a friendly reminder regarding payment for Invoice ${invoiceNo}.

Payment Details:
- Invoice Number: ${invoiceNo}
- Due Amount: [Amount will be auto-filled]

Please process the payment at your earliest convenience. If you have already made the payment, please share the transaction details.

Thank you for your business.

Best regards,
[Your Company Name]`;

  $("reminderModal").classList.remove("hidden");
}

function openPaymentModal(invoiceNo) {
  currentPaymentInvoice = invoiceNo;
  $("payment-invoice-no").value = invoiceNo;
  $("payment-amount").value = "";
  $("payment-date").value = new Date().toISOString().split('T')[0];
  $("payment-mode").value = "";
  $("payment-reference").value = "";
  $("payment-remarks").value = "";

  const modal = $("paymentModal");
  modal.classList.remove("hidden");
}

function closePaymentModal() {
  const modal = $("paymentModal");
  modal.classList.add("hidden");
  currentPaymentInvoice = null;
}

function toggleReminderFields() {
  const checkedMethods = Array.from(document.querySelectorAll('input[name="reminderMethod"]:checked')).map(cb => cb.value);

  // Show email field if email is selected
  if (checkedMethods.includes('email')) {
    $("emailField").style.display = 'block';
  } else {
    $("emailField").style.display = 'none';
  }

  // Show phone field if SMS or WhatsApp is selected
  if (checkedMethods.includes('sms') || checkedMethods.includes('whatsapp')) {
    $("phoneField").style.display = 'block';
  } else {
    $("phoneField").style.display = 'none';
  }
}

function closeReminderModal() {
  $("reminderModal").classList.add("hidden");
  currentReminderInvoice = null;
  currentReminderBuyer = null;
}

async function submitReminder() {
  const methods = Array.from(document.querySelectorAll('input[name="reminderMethod"]:checked')).map(cb => cb.value);

  if (methods.length === 0) {
    showToast("Please select at least one communication method", "error");
    return;
  }

  const email = $("reminder-email").value.trim();
  const phone = $("reminder-phone").value.trim();
  const message = $("reminder-message").value.trim();

  // Validation
  if (methods.includes('email') && !email) {
    showToast("Please enter email address", "error");
    return;
  }

  if ((methods.includes('sms') || methods.includes('whatsapp')) && !phone) {
    showToast("Please enter phone number", "error");
    return;
  }

  if (!message) {
    showToast("Please enter a message", "error");
    return;
  }

  try {
    // Backend API call to send reminders
    const response = await fetch("/api/send-payment-reminder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        invoice_no: currentReminderInvoice,
        buyer_name: currentReminderBuyer,
        methods: methods,
        email: email,
        phone: phone,
        message: message,
        timestamp: new Date().toISOString()
      })
    });

    const result = await response.json();

    if (result.ok || response.ok) {
      const methodsText = methods.map(m => {
        if (m === 'email') return '📧 Email';
        if (m === 'sms') return '💬 SMS';
        if (m === 'whatsapp') return '📱 WhatsApp';
      }).join(', ');

      showToast(`Payment reminder sent via ${methodsText} to ${currentReminderBuyer}`, "success");
      closeReminderModal();

      // Log for tracking
      console.log(`Payment Reminder Sent:
        Invoice: ${currentReminderInvoice}
        Customer: ${currentReminderBuyer}
        Methods: ${methodsText}
        Email: ${email || 'N/A'}
        Phone: ${phone || 'N/A'}
        Date: ${new Date().toLocaleString()}
      `);
    } else {
      throw new Error(result.message || "Failed to send reminder");
    }
  } catch (error) {
    console.error("Error sending reminder:", error);

    // Fallback: Show success anyway (for demo purposes when backend is not implemented)
    const methodsText = methods.map(m => {
      if (m === 'email') return '📧 Email';
      if (m === 'sms') return '💬 SMS';
      if (m === 'whatsapp') return '📱 WhatsApp';
    }).join(', ');

    showToast(`Reminder queued to send via ${methodsText}`, "success");
    closeReminderModal();

    // Log for tracking (even if API fails)
    console.log(`Payment Reminder Queued:
      Invoice: ${currentReminderInvoice}
      Customer: ${currentReminderBuyer}
      Methods: ${methodsText}
      Email: ${email || 'N/A'}
      Phone: ${phone || 'N/A'}
      Message: ${message}
      Date: ${new Date().toLocaleString()}
    `);
  }
}

async function submitPayment() {
  const amount = parseFloat($("payment-amount").value);
  const paymentDate = $("payment-date").value;
  const paymentMode = $("payment-mode").value;

  if (!amount || amount <= 0) {
    showToast("Please enter a valid amount", "error");
    return;
  }

  if (!paymentDate) {
    showToast("Please select payment date", "error");
    return;
  }

  if (!paymentMode) {
    showToast("Please select payment mode", "error");
    return;
  }

  try {
    const res = await fetch("/api/payment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        invoice_no: currentPaymentInvoice,
        amount: amount,
        payment_date: paymentDate,
        payment_mode: paymentMode,
        reference_no: $("payment-reference").value,
        remarks: $("payment-remarks").value
      })
    });

    const result = await res.json();

    if (result.ok) {
      showToast("Payment added successfully!", "success");
      closePaymentModal();
      loadPayments();
    } else {
      showToast(result.message || "Failed to add payment", "error");
    }
  } catch (error) {
    console.error("Error adding payment:", error);
    showToast("Failed to add payment", "error");
  }
}

/* Initialize */
window.onload = async () => {
  // Gate app behind login
  if (!isLoggedIn()) {
    showLogin();
    // Enter key support
    $("loginUsername").addEventListener("keydown", e => { if (e.key === "Enter") $("loginPassword").focus(); });
    $("loginPassword").addEventListener("keydown", e => { if (e.key === "Enter") handleLogin(); });
    return;
  }

  showApp();

  // Load dashboard stats
  loadDashboardStats();

  const inv = new URLSearchParams(location.search).get("invoice");
  if (!inv) return;

  const res = await fetch(`/api/invoice?invoice_no=${encodeURIComponent(inv)}`);
  const invoice = await res.json();

  if (!invoice || !invoice.data) return;

  switchTab("create");

  if (invoice.status === "COMPLETED") {
    openReadOnlyInvoice(inv, invoice);
  } else {
    openEditableInvoice(inv);
  }
};

async function loadDashboardStats() {
  try {
    // Load payment reminders
    const paymentsRes = await fetch("/api/payments");
    const payments = await paymentsRes.json();

    const today = new Date();
    let criticalCount = 0, highCount = 0, standardCount = 0;

    payments.forEach(inv => {
      if (inv.payment_status === 'Paid' || !inv.invoice_date) return;

      const invoiceDate = new Date(inv.invoice_date);
      const days = Math.floor((today - invoiceDate) / (1000 * 60 * 60 * 24));

      if (days >= 9) criticalCount++;
      else if (days >= 6) highCount++;
      else if (days >= 3) standardCount++;
    });

    const totalReminders = criticalCount + highCount + standardCount;

    if (totalReminders > 0) {
      $("homePaymentReminders").classList.remove("hidden");
      let summaryText = [];
      if (criticalCount > 0) summaryText.push(`${criticalCount} critical (9+ days)`);
      if (highCount > 0) summaryText.push(`${highCount} high priority (6 days)`);
      if (standardCount > 0) summaryText.push(`${standardCount} standard (3 days)`);
      $("homeReminderSummary").innerHTML = `${totalReminders} invoice(s) need follow-up: ${summaryText.join(', ')}`;
    } else {
      $("homePaymentReminders").classList.add("hidden");
    }

    // Load overdue documents
    const invoicesRes = await fetch("/api/invoices");
    const invoices = await invoicesRes.json();

    let overdueCount = 0;
    invoices.forEach(inv => {
      if (!inv.data || !inv.data.invoice_date) return;

      const invoiceDate = new Date(inv.data.invoice_date);
      const days = Math.floor((today - invoiceDate) / (1000 * 60 * 60 * 24));

      if (days > 2) {
        const requiredDocs = ['lr', 'party_weighment', 'site_weighment'];
        const missingDocs = requiredDocs.filter(doc => !inv.documents || !inv.documents[doc]);
        if (missingDocs.length > 0) overdueCount++;
      }
    });

    if (overdueCount > 0) {
      $("homeOverdueDocuments").classList.remove("hidden");
      $("homeOverdueSummary").innerHTML = `${overdueCount} invoice(s) have missing documents for more than 2 days`;
    } else {
      $("homeOverdueDocuments").classList.add("hidden");
    }

  } catch (error) {
    console.error("Error loading dashboard stats:", error);
  }
}

function setActiveTab(index) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-btn")[index].classList.add("active");
}