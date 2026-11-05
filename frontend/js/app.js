/**
 * AXIOM — Main Application Controller
 * Handles DOM interactions, navigation, drag-and-drop validation,
 * document library rendering, legal analysis display, and TF-IDF search.
 * Strictly vanilla JavaScript using native browser APIs and safe DOM manipulation.
 */

(function (window, document) {
  "use strict";

  // State Management
  const state = {
    activeTab: "overview",
    documents: [],
    selectedUploadFile: null,
    selectedAnalysisDocId: "",
    currentAnalysisData: null,
    activeClauseFilter: "ALL",
    activeModalDoc: null,
    isUploading: false,
    isSearching: false,
    isAnalyzing: false,
  };

  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
  const ALLOWED_EXTS = [".pdf", ".docx", ".txt"];

  const CLAUSE_CATEGORIES = [
    "Confidentiality and Non-Disclosure",
    "Termination and Default",
    "Indemnity and Hold Harmless",
    "Limitation of Liability",
    "Governing Law and Dispute Resolution",
    "Warranties and Representations",
    "Force Majeure",
    "Intellectual Property Rights",
  ];

  /* ==========================================================================
     DOM Elements Cache
     ========================================================================== */
  const elements = {};

  function initElements() {
    elements.tabButtons = document.querySelectorAll(".nav-tab-btn");
    elements.tabPanels = document.querySelectorAll(".tab-panel");
    elements.headerDocCount = document.getElementById("header-doc-count");
    elements.statTotalDocs = document.getElementById("stat-total-docs");

    // Upload
    elements.dropzone = document.getElementById("dropzone");
    elements.fileInput = document.getElementById("file-input");
    elements.btnBrowse = document.getElementById("btn-browse-file");
    elements.selectedFileBox = document.getElementById("selected-file-box");
    elements.previewFileName = document.getElementById("preview-file-name");
    elements.previewFileSize = document.getElementById("preview-file-size");
    elements.previewFileType = document.getElementById("preview-file-type");
    elements.btnCancelFile = document.getElementById("btn-cancel-file");
    elements.btnProcessUpload = document.getElementById("btn-process-upload");
    elements.uploadValidationMsg = document.getElementById("upload-validation-msg");
    elements.overviewRecentDocs = document.getElementById("overview-recent-docs");
    elements.btnViewAllDocs = document.getElementById("btn-view-all-docs");

    // Documents
    elements.docFilterInput = document.getElementById("doc-filter-input");
    elements.docFilterCount = document.getElementById("doc-filter-count");
    elements.documentsTableWrapper = document.getElementById("documents-table-wrapper");
    elements.btnNavUpload = document.getElementById("btn-nav-upload");
    elements.btnLibraryEmptyUpload = document.getElementById("btn-library-empty-upload");

    // Analysis
    elements.analysisDocSelect = document.getElementById("analysis-doc-select");
    elements.btnRunAnalysis = document.getElementById("btn-run-analysis");
    elements.analysisResultsContainer = document.getElementById("analysis-results-container");

    // Search
    elements.searchForm = document.getElementById("search-form");
    elements.searchQueryInput = document.getElementById("search-query-input");
    elements.searchScopeSelect = document.getElementById("search-scope-select");
    elements.searchTopKSelect = document.getElementById("search-topk-select");
    elements.searchResultsArea = document.getElementById("search-results-area");
    elements.btnSubmitSearch = document.getElementById("btn-submit-search");

    // Modal
    elements.docModal = document.getElementById("doc-modal");
    elements.modalDocTitle = document.getElementById("modal-doc-title");
    elements.modalDocBody = document.getElementById("modal-doc-body");
    elements.btnCloseModal = document.getElementById("btn-close-modal");
    elements.btnCopyDocText = document.getElementById("btn-copy-doc-text");
    elements.btnAnalyzeModalDoc = document.getElementById("btn-analyze-modal-doc");

    // Mobile
    elements.mobileToggle = document.getElementById("mobile-toggle");
  }

  /* ==========================================================================
     Helper Utilities
     ========================================================================== */
  function formatBytes(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  function formatDate(isoString) {
    if (!isoString) return "N/A";
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString;
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function highlightMatches(text, query) {
    if (!text) return "";
    if (!query) return escapeHtml(text);

    const safeText = escapeHtml(text);
    const words = query
      .trim()
      .split(/\s+/)
      .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
      .filter((w) => w.length >= 3);

    if (words.length === 0) return safeText;

    const regex = new RegExp(`\\b(${words.join("|")})\\b`, "gi");
    return safeText.replace(regex, '<mark class="highlight">$1</mark>');
  }

  /* ==========================================================================
     Navigation & Tab Management
     ========================================================================== */
  function switchTab(tabName) {
    if (!tabName) return;
    state.activeTab = tabName;

    elements.tabButtons.forEach((btn) => {
      const isTarget = btn.getAttribute("data-tab") === tabName;
      btn.classList.toggle("active", isTarget);
      btn.setAttribute("aria-selected", isTarget ? "true" : "false");
    });

    elements.tabPanels.forEach((panel) => {
      const isTarget = panel.id === `panel-${tabName}`;
      panel.classList.toggle("active", isTarget);
    });

    // Hash update without scroll jump
    if (history.replaceState) {
      history.replaceState(null, null, `#${tabName}`);
    }

    // Refresh views if necessary
    if (tabName === "documents") {
      renderDocumentsLibrary();
    } else if (tabName === "analysis") {
      populateAnalysisDropdown();
    } else if (tabName === "search") {
      populateSearchScope();
    }
  }

  /* ==========================================================================
     File Drag-and-Drop & Upload Validation
     ========================================================================== */
  function validateSelectedFile(file) {
    if (!file) {
      return { valid: false, error: "No file was selected." };
    }

    const name = file.name.toLowerCase();
    const hasValidExt = ALLOWED_EXTS.some((ext) => name.endsWith(ext));

    if (!hasValidExt) {
      return {
        valid: false,
        error: `Unsupported format. Allowed formats: ${ALLOWED_EXTS.join(", ")}.`,
      };
    }

    if (file.size === 0) {
      return { valid: false, error: "The selected file is empty (0 Bytes)." };
    }

    if (file.size > MAX_FILE_SIZE) {
      return {
        valid: false,
        error: `File size (${formatBytes(file.size)}) exceeds the maximum permitted limit of 10 MB.`,
      };
    }

    return { valid: true };
  }

  function handleFileSelected(file) {
    hideUploadValidation();

    const validation = validateSelectedFile(file);
    if (!validation.valid) {
      state.selectedUploadFile = null;
      showUploadValidation(validation.error, "error");
      elements.selectedFileBox.style.display = "none";
      return;
    }

    state.selectedUploadFile = file;

    // Determine badge type
    const ext = file.name.split(".").pop().toUpperCase();
    elements.previewFileName.textContent = file.name;
    elements.previewFileSize.textContent = formatBytes(file.size);
    elements.previewFileType.textContent = ext;

    elements.selectedFileBox.style.display = "flex";
  }

  function clearSelectedFile() {
    state.selectedUploadFile = null;
    elements.fileInput.value = "";
    elements.selectedFileBox.style.display = "none";
    hideUploadValidation();
  }

  function showUploadValidation(message, type = "error") {
    elements.uploadValidationMsg.className = `alert alert-${type}`;
    elements.uploadValidationMsg.textContent = message;
    elements.uploadValidationMsg.style.display = "block";
  }

  function hideUploadValidation() {
    elements.uploadValidationMsg.style.display = "none";
    elements.uploadValidationMsg.textContent = "";
  }

  /* ==========================================================================
     Backend Data Synchronization
     ========================================================================== */
  async function refreshDocumentsList() {
    try {
      const response = await window.LexiScopeAPI.listDocuments();
      state.documents = (response && response.documents) || [];
      updateHeaderCounts();
      renderRecentDocumentsOverview();
      renderDocumentsLibrary();
      populateAnalysisDropdown();
      populateSearchScope();
    } catch (err) {
      // Backend not yet available or offline; show graceful empty states
      state.documents = [];
      updateHeaderCounts();
      renderRecentDocumentsOverview();
      renderDocumentsLibrary();
    }
  }

  function updateHeaderCounts() {
    const count = state.documents.length;
    if (elements.headerDocCount) elements.headerDocCount.textContent = count;
    if (elements.statTotalDocs) elements.statTotalDocs.textContent = count;
    if (elements.docFilterCount) {
      elements.docFilterCount.textContent = `Showing ${count} document${count === 1 ? "" : "s"}`;
    }
  }

  /* ==========================================================================
     Document Upload Execution
     ========================================================================== */
  async function executeUpload() {
    if (!state.selectedUploadFile) return;

    state.isUploading = true;
    elements.btnProcessUpload.disabled = true;
    elements.btnProcessUpload.textContent = "Ingesting Document...";

    try {
      const newDoc = await window.LexiScopeAPI.uploadDocument(state.selectedUploadFile);
      showUploadValidation(`Document '${newDoc.filename}' successfully uploaded and indexed!`, "success");
      clearSelectedFile();
      await refreshDocumentsList();
    } catch (err) {
      showUploadValidation(err.message || "Failed to upload document to backend.", "error");
    } finally {
      state.isUploading = false;
      elements.btnProcessUpload.disabled = false;
      elements.btnProcessUpload.textContent = "Upload & Extract Document";
    }
  }

  /* ==========================================================================
     Render: Overview Recent Documents
     ========================================================================== */
  function renderRecentDocumentsOverview() {
    if (!elements.overviewRecentDocs) return;

    if (state.documents.length === 0) {
      elements.overviewRecentDocs.innerHTML = `
        <div class="empty-state">
          <svg class="empty-state-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h3 class="empty-state-title">No Documents Loaded Yet</h3>
          <p class="empty-state-text">
            Upload a legal contract, agreement, or memorandum above to extract text, inspect clauses, and run TF-IDF passage retrieval.
          </p>
        </div>
      `;
      return;
    }

    const recent = state.documents.slice(-4).reverse();
    const rowsHtml = recent
      .map(
        (doc) => `
        <tr>
          <td>
            <div style="font-weight: 600; color: var(--primary);">${escapeHtml(doc.filename)}</div>
            <div style="font-size: 0.78rem; font-family: var(--font-mono); color: var(--text-muted);">${escapeHtml(doc.id.substring(0, 13))}...</div>
          </td>
          <td><span class="badge badge-${doc.file_type}">${doc.file_type.toUpperCase()}</span></td>
          <td>${formatBytes(doc.file_size_bytes)}</td>
          <td>${doc.word_count.toLocaleString()} words</td>
          <td>${doc.page_count} page${doc.page_count === 1 ? "" : "s"}</td>
          <td>${formatDate(doc.uploaded_at)}</td>
          <td style="text-align: right;">
            <button class="btn btn-secondary btn-sm" onclick="LexiScopeApp.inspectDocument('${doc.id}')">View</button>
            <button class="btn btn-primary btn-sm" onclick="LexiScopeApp.startAnalysis('${doc.id}')">Analyze</button>
          </td>
        </tr>
      `
      )
      .join("");

    elements.overviewRecentDocs.innerHTML = `
      <div class="table-container">
        <table class="doc-table">
          <thead>
            <tr>
              <th>Document</th>
              <th>Format</th>
              <th>Size</th>
              <th>Length</th>
              <th>Pages</th>
              <th>Uploaded</th>
              <th style="text-align: right;">Actions</th>
            </tr>
          </thead>
          <tbody>${rowsHtml}</tbody>
        </table>
      </div>
    `;
  }

  /* ==========================================================================
     Render: Documents Library
     ========================================================================== */
  function renderDocumentsLibrary() {
    if (!elements.documentsTableWrapper) return;

    const filterText = (elements.docFilterInput ? elements.docFilterInput.value : "").trim().toLowerCase();
    const filteredDocs = state.documents.filter(
      (d) =>
        d.filename.toLowerCase().includes(filterText) ||
        d.file_type.toLowerCase().includes(filterText)
    );

    if (elements.docFilterCount) {
      elements.docFilterCount.textContent = `Showing ${filteredDocs.length} of ${state.documents.length} document${state.documents.length === 1 ? "" : "s"}`;
    }

    if (filteredDocs.length === 0) {
      const isFiltered = filterText.length > 0;
      elements.documentsTableWrapper.innerHTML = `
        <div class="empty-state">
          <svg class="empty-state-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          <h3 class="empty-state-title">${isFiltered ? "No Matching Documents Found" : "The Document Library is Empty"}</h3>
          <p class="empty-state-text">
            ${
              isFiltered
                ? `No documents matched the filter "${escapeHtml(filterText)}". Try clearing your search term.`
                : "No legal files have been added to the session memory yet. Use the upload tool to load a PDF, DOCX, or TXT file."
            }
          </p>
          ${
            !isFiltered
              ? '<button class="btn btn-secondary btn-sm" onclick="LexiScopeApp.switchTab(\'overview\')">Upload Document Now</button>'
              : ""
          }
        </div>
      `;
      return;
    }

    const rowsHtml = filteredDocs
      .map(
        (doc) => `
        <tr>
          <td>
            <div style="font-weight: 600; color: var(--primary);">${escapeHtml(doc.filename)}</div>
            <div style="font-size: 0.76rem; font-family: var(--font-mono); color: var(--text-muted);">ID: ${escapeHtml(doc.id)}</div>
          </td>
          <td><span class="badge badge-${doc.file_type}">${doc.file_type.toUpperCase()}</span></td>
          <td>${formatBytes(doc.file_size_bytes)}</td>
          <td>${doc.word_count.toLocaleString()}</td>
          <td>${doc.page_count}</td>
          <td>${formatDate(doc.uploaded_at)}</td>
          <td style="text-align: right; white-space: nowrap;">
            <button class="btn btn-secondary btn-sm" onclick="LexiScopeApp.inspectDocument('${doc.id}')">View Text</button>
            <button class="btn btn-primary btn-sm" onclick="LexiScopeApp.startAnalysis('${doc.id}')">Analyze</button>
            <button class="btn btn-danger btn-sm" onclick="LexiScopeApp.removeDocument('${doc.id}')" title="Delete document">✕</button>
          </td>
        </tr>
      `
      )
      .join("");

    elements.documentsTableWrapper.innerHTML = `
      <div class="table-container">
        <table class="doc-table">
          <thead>
            <tr>
              <th>Document Details</th>
              <th>Format</th>
              <th>File Size</th>
              <th>Words</th>
              <th>Pages</th>
              <th>Ingested</th>
              <th style="text-align: right;">Actions</th>
            </tr>
          </thead>
          <tbody>${rowsHtml}</tbody>
        </table>
      </div>
    `;
  }

  /* ==========================================================================
     Analysis Tab Controllers
     ========================================================================== */
  function populateAnalysisDropdown() {
    if (!elements.analysisDocSelect) return;

    const currentVal = elements.analysisDocSelect.value || state.selectedAnalysisDocId;
    elements.analysisDocSelect.innerHTML = '<option value="">-- Select a Loaded Document --</option>';

    state.documents.forEach((doc) => {
      const opt = document.createElement("option");
      opt.value = doc.id;
      opt.textContent = `${doc.filename} (${doc.file_type.toUpperCase()} • ${doc.word_count.toLocaleString()} words)`;
      elements.analysisDocSelect.appendChild(opt);
    });

    if (currentVal && state.documents.some((d) => d.id === currentVal)) {
      elements.analysisDocSelect.value = currentVal;
      elements.btnRunAnalysis.disabled = false;
    } else {
      elements.btnRunAnalysis.disabled = true;
    }
  }

  async function executeAnalysis() {
    const docId = elements.analysisDocSelect.value || state.selectedAnalysisDocId;
    if (!docId) return;

    state.isAnalyzing = true;
    elements.btnRunAnalysis.disabled = true;
    elements.btnRunAnalysis.textContent = "Analyzing...";

    elements.analysisResultsContainer.innerHTML = `
      <div class="card" style="text-align: center; padding: 3rem 1.5rem;">
        <div style="font-size: 1.15rem; color: var(--primary); font-weight: 600; margin-bottom: 0.5rem;">
          Performing NLP Legal Analysis...
        </div>
        <p class="stat-desc">Computing descriptive metrics, sentence centrality TF-IDF summary, and rule-based clause detection.</p>
      </div>
    `;

    try {
      const result = await window.LexiScopeAPI.analyzeDocument(docId, 4);
      state.currentAnalysisData = result;
      state.activeClauseFilter = "ALL";
      renderAnalysisResults(result);
    } catch (err) {
      elements.analysisResultsContainer.innerHTML = `
        <div class="alert alert-error">
          <strong>Analysis Error:</strong> ${escapeHtml(err.message || "Could not analyze the selected document.")}
        </div>
      `;
    } finally {
      state.isAnalyzing = false;
      elements.btnRunAnalysis.disabled = false;
      elements.btnRunAnalysis.textContent = "Analyze Document";
    }
  }

  function renderAnalysisResults(data) {
    if (!data) return;

    const stats = data.statistics;
    const summary = data.summary;
    const clauses = data.detected_clauses || [];

    // Filter clauses by active category filter
    const visibleClauses =
      state.activeClauseFilter === "ALL"
        ? clauses
        : clauses.filter((c) => c.category === state.activeClauseFilter);

    // Filter Chips HTML
    const categoryCounts = {};
    clauses.forEach((c) => {
      categoryCounts[c.category] = (categoryCounts[c.category] || 0) + 1;
    });

    const filterChipsHtml = [
      `<button class="filter-chip ${state.activeClauseFilter === "ALL" ? "active" : ""}" onclick="LexiScopeApp.setClauseFilter('ALL')">All Clauses (${clauses.length})</button>`,
      ...CLAUSE_CATEGORIES.map((cat) => {
        const count = categoryCounts[cat] || 0;
        const isActive = state.activeClauseFilter === cat;
        return `<button class="filter-chip ${isActive ? "active" : ""}" onclick="LexiScopeApp.setClauseFilter('${escapeHtml(cat)}')">${escapeHtml(cat)} (${count})</button>`;
      }),
    ].join("");

    // Clause Cards HTML
    const clauseCardsHtml =
      visibleClauses.length === 0
        ? `
        <div class="empty-state" style="padding: 2rem 1.5rem;">
          <p class="empty-state-text">No detected clauses matched the selected filter.</p>
        </div>
      `
        : visibleClauses
            .map(
              (c) => `
        <div class="clause-card">
          <div class="clause-card-header">
            <span class="clause-category-name">${escapeHtml(c.category)}</span>
            <div class="clause-meta-tags">
              <span class="badge badge-sage">${escapeHtml(c.source_location)}</span>
              <span class="badge badge-burgundy" title="Heuristic rule confidence score">
                Confidence: ${(c.confidence * 100).toFixed(0)}% (Heuristic)
              </span>
            </div>
          </div>
          <div class="clause-text">
            &ldquo;${escapeHtml(c.matched_text)}&rdquo;
          </div>
          <div class="clause-keywords">
            <span>Matched Keywords:</span>
            ${c.matched_keywords.map((kw) => `<span class="kw-tag">${escapeHtml(kw)}</span>`).join("")}
          </div>
        </div>
      `
            )
            .join("");

    // Entities HTML (Dates, Amounts, Emails, Terms)
    const datesListHtml =
      stats.dates && stats.dates.length
        ? stats.dates.map((d) => `<span class="badge badge-sage" style="margin: 2px;">${escapeHtml(d)}</span>`).join("")
        : '<span class="stat-desc">No specific dates detected</span>';

    const amountsListHtml =
      stats.monetary_amounts && stats.monetary_amounts.length
        ? stats.monetary_amounts.map((a) => `<span class="badge badge-burgundy" style="margin: 2px;">${escapeHtml(a)}</span>`).join("")
        : '<span class="stat-desc">No monetary figures detected</span>';

    const emailsListHtml =
      stats.emails && stats.emails.length
        ? stats.emails.map((e) => `<span class="badge badge-txt" style="margin: 2px;">${escapeHtml(e)}</span>`).join("")
        : '<span class="stat-desc">No email addresses detected</span>';

    const topTermsListHtml =
      stats.top_terms && stats.top_terms.length
        ? stats.top_terms.map((t) => `<span class="kw-tag" style="margin: 2px;">${escapeHtml(t.term)} (${t.count})</span>`).join("")
        : '<span class="stat-desc">No terms extracted</span>';

    elements.analysisResultsContainer.innerHTML = `
      <!-- Stats Row -->
      <div class="grid-4" style="margin-bottom: 1.5rem;">
        <div class="stat-box">
          <span class="stat-label">Total Words</span>
          <span class="stat-value">${stats.word_count.toLocaleString()}</span>
          <span class="stat-desc">Parsed tokens</span>
        </div>
        <div class="stat-box">
          <span class="stat-label">Total Sentences</span>
          <span class="stat-value">${stats.sentence_count}</span>
          <span class="stat-desc">Sentence units</span>
        </div>
        <div class="stat-box">
          <span class="stat-label">Total Paragraphs</span>
          <span class="stat-value">${stats.paragraph_count}</span>
          <span class="stat-desc">Document sections</span>
        </div>
        <div class="stat-box">
          <span class="stat-label">Compression Ratio</span>
          <span class="stat-value">${(summary.compression_ratio * 100).toFixed(1)}%</span>
          <span class="stat-desc">Summary vs original text</span>
        </div>
      </div>

      <!-- Extractive Summary Block -->
      <div class="analysis-summary-block">
        <div class="analysis-summary-header">
          <h2 class="card-title">Extractive TF-IDF Summary</h2>
          <span class="badge badge-sage">Original Wording Verbatim • ${summary.sentence_count} Sentences</span>
        </div>
        <div class="summary-text-passage">
          ${escapeHtml(summary.full_summary)}
        </div>
      </div>

      <!-- Extracted Entities Grid -->
      <div class="grid-2" style="margin-bottom: 2rem;">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title" style="font-size: 1.1rem;">Important Dates</h3>
          </div>
          <div>${datesListHtml}</div>
        </div>
        <div class="card">
          <div class="card-header">
            <h3 class="card-title" style="font-size: 1.1rem;">Monetary Figures</h3>
          </div>
          <div>${amountsListHtml}</div>
        </div>
        <div class="card">
          <div class="card-header">
            <h3 class="card-title" style="font-size: 1.1rem;">Contact Emails</h3>
          </div>
          <div>${emailsListHtml}</div>
        </div>
        <div class="card">
          <div class="card-header">
            <h3 class="card-title" style="font-size: 1.1rem;">Frequently Occurring Key Terms</h3>
          </div>
          <div>${topTermsListHtml}</div>
        </div>
      </div>

      <!-- Detected Legal Clauses Section -->
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">Detected Legal Clauses (${clauses.length})</h2>
          <span class="stat-desc">Rule-based classification across 8 core categories</span>
        </div>

        <!-- Filter Chips -->
        <div class="filter-bar">${filterChipsHtml}</div>

        <!-- Clause Cards Container -->
        <div>${clauseCardsHtml}</div>
      </div>
    `;
  }

  /* ==========================================================================
     Search Tab Controllers
     ========================================================================== */
  function populateSearchScope() {
    if (!elements.searchScopeSelect) return;

    elements.searchScopeSelect.innerHTML = '<option value="all">All Indexed Documents</option>';
    state.documents.forEach((doc) => {
      const opt = document.createElement("option");
      opt.value = doc.id;
      opt.textContent = `${doc.filename} (${doc.file_type.toUpperCase()})`;
      elements.searchScopeSelect.appendChild(opt);
    });
  }

  async function executeSearch(e) {
    if (e && e.preventDefault) e.preventDefault();

    const query = elements.searchQueryInput.value.trim();
    if (!query) return;

    const scopeVal = elements.searchScopeSelect.value;
    const documentIds = scopeVal === "all" ? null : [scopeVal];
    const topK = parseInt(elements.searchTopKSelect.value, 10) || 5;

    state.isSearching = true;
    elements.btnSubmitSearch.disabled = true;
    elements.btnSubmitSearch.textContent = "Retrieving...";

    elements.searchResultsArea.innerHTML = `
      <div class="card" style="text-align: center; padding: 3rem 1.5rem;">
        <div style="font-size: 1.15rem; color: var(--primary); font-weight: 600; margin-bottom: 0.5rem;">
          Retrieving Passages via TF-IDF & Cosine Similarity...
        </div>
        <p class="stat-desc">Searching across indexed document chunks and ranking matching passages.</p>
      </div>
    `;

    try {
      const response = await window.LexiScopeAPI.searchDocuments(query, documentIds, topK);
      renderSearchResults(response);
    } catch (err) {
      elements.searchResultsArea.innerHTML = `
        <div class="alert alert-error">
          <strong>Search Error:</strong> ${escapeHtml(err.message || "Failed to execute search.")}
        </div>
      `;
    } finally {
      state.isSearching = false;
      elements.btnSubmitSearch.disabled = false;
      elements.btnSubmitSearch.textContent = "Retrieve Passages";
    }
  }

  function renderSearchResults(response) {
    if (!response || !response.results || response.results.length === 0) {
      elements.searchResultsArea.innerHTML = `
        <div class="empty-state">
          <svg class="empty-state-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 class="empty-state-title">No Matching Passages Found</h3>
          <p class="empty-state-text">
            No document passages matched the query &ldquo;${escapeHtml(response ? response.query : "")}&rdquo; above the similarity threshold.
            Try using broader legal terminology or ensure the relevant document has been uploaded.
          </p>
        </div>
      `;
      return;
    }

    const cardsHtml = response.results
      .map((item, idx) => {
        const highlightedSnippet = highlightMatches(item.matched_snippet, response.query);
        const highlightedFullChunk = highlightMatches(item.full_chunk_text, response.query);
        const chunkId = `chunk-expand-${idx}`;

        const pageDisplay = item.page_number ? `Page ${item.page_number}` : "Page N/A";
        const sectionDisplay = item.section_reference ? escapeHtml(item.section_reference) : "Body";

        return `
        <div class="search-result-card">
          <div class="search-result-header">
            <div class="source-attribution">
              <span class="doc-title">${escapeHtml(item.document_name)}</span>
              <span>•</span>
              <span class="badge badge-sage">${pageDisplay}</span>
              <span>•</span>
              <span class="badge badge-sage">${sectionDisplay}</span>
              <span>•</span>
              <span style="color: var(--text-muted);">Chunk #${item.chunk_index}</span>
            </div>
            <div class="score-badge" title="Cosine Similarity Score">
              Relevance: ${(item.score * 100).toFixed(1)}%
            </div>
          </div>

          <div class="passage-snippet">
            ${highlightedSnippet}
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem;">
            <button class="btn btn-secondary btn-sm" onclick="LexiScopeApp.toggleChunk('${chunkId}')" id="btn-${chunkId}">
              View Full Chunk Passage ▾
            </button>
            <button class="btn btn-secondary btn-sm" onclick="LexiScopeApp.inspectDocument('${item.document_id}')">
              Open Full Document
            </button>
          </div>

          <div id="${chunkId}" style="display: none; margin-top: 0.85rem; padding: 1rem; background-color: var(--bg-surface-alt); border-radius: var(--radius-sm); border: 1px solid var(--border-light); font-size: 0.92rem; line-height: 1.6;">
            ${highlightedFullChunk}
          </div>
        </div>
      `;
      })
      .join("");

    elements.searchResultsArea.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
        <h2 class="card-title" style="font-size: 1.2rem;">
          Retrieved ${response.total_matches} Passage${response.total_matches === 1 ? "" : "s"}
        </h2>
        <span class="stat-desc">Execution time: ${response.execution_time_ms} ms</span>
      </div>
      <div>${cardsHtml}</div>
    `;
  }

  /* ==========================================================================
     Modal Document Inspector
     ========================================================================== */
  async function inspectDocument(docId) {
    if (!docId) return;

    elements.modalDocTitle.textContent = "Loading Document Details...";
    elements.modalDocBody.innerHTML = '<div style="text-align: center; padding: 2rem;">Retrieving extracted document text and sections...</div>';
    elements.docModal.classList.add("active");

    try {
      const doc = await window.LexiScopeAPI.getDocument(docId);
      state.activeModalDoc = doc;

      elements.modalDocTitle.textContent = `${doc.metadata.filename} (${doc.metadata.file_type.toUpperCase()})`;

      const sectionsHtml = doc.sections
        .map(
          (s) => `
          <div style="margin-bottom: 1.25rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border-light);">
            <div style="display: flex; gap: 0.5rem; margin-bottom: 0.35rem; align-items: center;">
              <span class="badge badge-sage">Page ${s.page_number || "1"}</span>
              ${s.heading ? `<strong style="color: var(--primary); font-size: 0.92rem;">${escapeHtml(s.heading)}</strong>` : ""}
              <span style="font-size: 0.78rem; color: var(--text-muted);">${s.word_count} words</span>
            </div>
            <div style="font-size: 0.92rem; line-height: 1.65; color: var(--text-primary); white-space: pre-wrap;">${escapeHtml(s.text)}</div>
          </div>
        `
        )
        .join("");

      elements.modalDocBody.innerHTML = `
        <div style="background-color: var(--bg-secondary); padding: 0.85rem 1.25rem; border-radius: var(--radius-sm); margin-bottom: 1.25rem; font-size: 0.85rem; display: flex; gap: 1.5rem; flex-wrap: wrap;">
          <div><strong>Size:</strong> ${formatBytes(doc.metadata.file_size_bytes)}</div>
          <div><strong>Total Words:</strong> ${doc.metadata.word_count.toLocaleString()}</div>
          <div><strong>Total Pages:</strong> ${doc.metadata.page_count}</div>
          <div><strong>Sections:</strong> ${doc.sections.length}</div>
        </div>
        <div>${sectionsHtml}</div>
      `;
    } catch (err) {
      elements.modalDocBody.innerHTML = `
        <div class="alert alert-error">
          Failed to load document text: ${escapeHtml(err.message)}
        </div>
      `;
    }
  }

  function closeModal() {
    elements.docModal.classList.remove("active");
    state.activeModalDoc = null;
  }

  function copyModalText() {
    if (!state.activeModalDoc || !state.activeModalDoc.full_text) return;
    navigator.clipboard
      .writeText(state.activeModalDoc.full_text)
      .then(() => {
        elements.btnCopyDocText.textContent = "Copied!";
        setTimeout(() => {
          elements.btnCopyDocText.textContent = "Copy Full Text";
        }, 2000);
      })
      .catch(() => {
        elements.btnCopyDocText.textContent = "Copy Failed";
      });
  }

  async function removeDocument(docId) {
    if (!confirm("Are you sure you want to remove this document from the current session?")) {
      return;
    }
    try {
      await window.LexiScopeAPI.deleteDocument(docId);
      await refreshDocumentsList();
      if (state.selectedAnalysisDocId === docId) {
        state.selectedAnalysisDocId = "";
        state.currentAnalysisData = null;
        elements.analysisResultsContainer.innerHTML = `
          <div class="empty-state">
            <h3 class="empty-state-title">No Document Selected for Analysis</h3>
            <p class="empty-state-text">The previously analyzed document was removed from session memory.</p>
          </div>
        `;
      }
    } catch (err) {
      alert(`Error removing document: ${err.message}`);
    }
  }

  /* ==========================================================================
     Global Public Interface
     ========================================================================== */
  window.LexiScopeApp = {
    switchTab,
    inspectDocument,
    removeDocument,
    startAnalysis: function (docId) {
      state.selectedAnalysisDocId = docId;
      switchTab("analysis");
      if (elements.analysisDocSelect) {
        elements.analysisDocSelect.value = docId;
        elements.btnRunAnalysis.disabled = false;
      }
      executeAnalysis();
    },
    setClauseFilter: function (category) {
      state.activeClauseFilter = category;
      if (state.currentAnalysisData) {
        renderAnalysisResults(state.currentAnalysisData);
      }
    },
    toggleChunk: function (elementId) {
      const el = document.getElementById(elementId);
      const btn = document.getElementById(`btn-${elementId}`);
      if (!el || !btn) return;
      if (el.style.display === "none") {
        el.style.display = "block";
        btn.textContent = "Collapse Chunk Passage ▴";
      } else {
        el.style.display = "none";
        btn.textContent = "View Full Chunk Passage ▾";
      }
    },
  };

  window.AxiomApp = window.LexiScopeApp;

  /* ==========================================================================
     Event Listeners Binding
     ========================================================================== */
  function bindEvents() {
    // Tab switching
    elements.tabButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-tab");
        switchTab(tab);
      });
    });

    // Mobile menu toggle
    if (elements.mobileToggle) {
      elements.mobileToggle.addEventListener("click", () => {
        const nav = document.querySelector(".nav-wrapper");
        if (nav) nav.classList.toggle("mobile-open");
      });
    }

    // Dropzone Events
    if (elements.dropzone) {
      ["dragenter", "dragover"].forEach((eventName) => {
        elements.dropzone.addEventListener(
          eventName,
          (e) => {
            e.preventDefault();
            e.stopPropagation();
            elements.dropzone.classList.add("dragover");
          },
          false
        );
      });

      ["dragleave", "drop"].forEach((eventName) => {
        elements.dropzone.addEventListener(
          eventName,
          (e) => {
            e.preventDefault();
            e.stopPropagation();
            elements.dropzone.classList.remove("dragover");
          },
          false
        );
      });

      elements.dropzone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
          handleFileSelected(files[0]);
        }
      });

      elements.dropzone.addEventListener("click", (e) => {
        // Prevent re-triggering if browse button was clicked
        if (e.target !== elements.btnBrowse) {
          elements.fileInput.click();
        }
      });
    }

    if (elements.btnBrowse) {
      elements.btnBrowse.addEventListener("click", (e) => {
        e.stopPropagation();
        elements.fileInput.click();
      });
    }

    if (elements.fileInput) {
      elements.fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length > 0) {
          handleFileSelected(e.target.files[0]);
        }
      });
    }

    if (elements.btnCancelFile) {
      elements.btnCancelFile.addEventListener("click", clearSelectedFile);
    }

    if (elements.btnProcessUpload) {
      elements.btnProcessUpload.addEventListener("click", executeUpload);
    }

    if (elements.btnViewAllDocs) {
      elements.btnViewAllDocs.addEventListener("click", () => switchTab("documents"));
    }

    if (elements.btnNavUpload) {
      elements.btnNavUpload.addEventListener("click", () => switchTab("overview"));
    }

    if (elements.btnLibraryEmptyUpload) {
      elements.btnLibraryEmptyUpload.addEventListener("click", () => switchTab("overview"));
    }

    // Documents Library filter input
    if (elements.docFilterInput) {
      elements.docFilterInput.addEventListener("input", renderDocumentsLibrary);
    }

    // Analysis doc selection
    if (elements.analysisDocSelect) {
      elements.analysisDocSelect.addEventListener("change", (e) => {
        state.selectedAnalysisDocId = e.target.value;
        elements.btnRunAnalysis.disabled = !e.target.value;
      });
    }

    if (elements.btnRunAnalysis) {
      elements.btnRunAnalysis.addEventListener("click", executeAnalysis);
    }

    // Search form submission
    if (elements.searchForm) {
      elements.searchForm.addEventListener("submit", executeSearch);
    }

    // Modal controls
    if (elements.btnCloseModal) {
      elements.btnCloseModal.addEventListener("click", closeModal);
    }

    if (elements.docModal) {
      elements.docModal.addEventListener("click", (e) => {
        if (e.target === elements.docModal) closeModal();
      });
    }

    if (elements.btnCopyDocText) {
      elements.btnCopyDocText.addEventListener("click", copyModalText);
    }

    if (elements.btnAnalyzeModalDoc) {
      elements.btnAnalyzeModalDoc.addEventListener("click", () => {
        if (state.activeModalDoc) {
          const docId = state.activeModalDoc.metadata.id;
          closeModal();
          window.LexiScopeApp.startAnalysis(docId);
        }
      });
    }

    // Keyboard ESC to close modal
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && elements.docModal.classList.contains("active")) {
        closeModal();
      }
    });

    // Handle browser hash navigation on load
    window.addEventListener("hashchange", () => {
      const hash = window.location.hash.replace("#", "");
      if (["overview", "documents", "analysis", "search"].includes(hash)) {
        switchTab(hash);
      }
    });
  }

  /* ==========================================================================
     Application Initialization
     ========================================================================== */
  document.addEventListener("DOMContentLoaded", () => {
    initElements();
    bindEvents();

    // Check initial hash
    const initialHash = window.location.hash.replace("#", "");
    if (["overview", "documents", "analysis", "search"].includes(initialHash)) {
      switchTab(initialHash);
    } else {
      switchTab("overview");
    }

    // Sync initial state with backend
    refreshDocumentsList();
  });
})(window, document);
