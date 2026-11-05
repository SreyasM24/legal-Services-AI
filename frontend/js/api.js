/**
 * AXIOM — API Client Module
 * Maps directly to backend/app/schemas.py and backend/app/api/routes.py.
 * Pure Vanilla JavaScript using native fetch API.
 */

(function (window) {
  "use strict";

  // Same-origin API base path; avoids hardcoded hostnames and resolves cleanly on any host:port
  const API_BASE = window.AXIOM_API_BASE || window.LEXISCOPE_API_BASE || "/api";

  /**
   * Helper to execute fetch requests with unified error handling
   * @param {string} endpoint - API path relative to base
   * @param {object} options - Fetch options
   * @returns {Promise<any>}
   */
  async function request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    
    // Default headers if not sending FormData
    const isFormData = options.body instanceof FormData;
    const headers = isFormData
      ? { ...(options.headers || {}) }
      : {
          "Content-Type": "application/json",
          Accept: "application/json",
          ...(options.headers || {}),
        };

    try {
      const response = await fetch(url, { ...options, headers });

      // Handle 204 No Content
      if (response.status === 204) {
        return null;
      }

      // Parse JSON response or fallback to text
      let data;
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        data = await response.json();
      } else {
        data = { detail: await response.text() };
      }

      // Check HTTP status code
      if (!response.ok) {
        const errorMessage = data && data.detail ? data.detail : `HTTP Error ${response.status}: ${response.statusText}`;
        const error = new Error(errorMessage);
        error.status = response.status;
        error.data = data;
        throw error;
      }

      return data;
    } catch (err) {
      if (err.name === "TypeError" && err.message.includes("fetch")) {
        const netErr = new Error("Unable to connect to LexiScope backend. Please ensure the server is running on http://127.0.0.1:8000.");
        netErr.status = 0;
        netErr.isNetworkError = true;
        throw netErr;
      }
      throw err;
    }
  }

  const LexiScopeAPI = {
    getBaseUrl: () => API_BASE,

    /**
     * Check backend health and engine availability
     * GET /api/health
     * @returns {Promise<HealthResponse>}
     */
    async checkHealth() {
      return request("/health", { method: "GET" });
    },

    /**
     * Upload and extract text from PDF, DOCX, or TXT
     * POST /api/documents/upload
     * @param {File} file - File object from browser file input
     * @returns {Promise<DocumentMetadata>}
     */
    async uploadDocument(file) {
      if (!file) {
        throw new Error("No file specified for upload.");
      }
      const formData = new FormData();
      formData.append("file", file, file.name);

      return request("/documents/upload", {
        method: "POST",
        body: formData,
      });
    },

    /**
     * List all documents currently stored in the session
     * GET /api/documents
     * @returns {Promise<DocumentListResponse>}
     */
    async listDocuments() {
      return request("/documents", { method: "GET" });
    },

    /**
     * Retrieve document details, sections, and full text
     * GET /api/documents/{doc_id}
     * @param {string} docId - Unique document UUID
     * @returns {Promise<DocumentDetailResponse>}
     */
    async getDocument(docId) {
      if (!docId) throw new Error("Document ID is required.");
      return request(`/documents/${encodeURIComponent(docId)}`, { method: "GET" });
    },

    /**
     * Remove a document from session storage
     * DELETE /api/documents/{doc_id}
     * @param {string} docId - Unique document UUID
     * @returns {Promise<{message: string, remaining_documents: number}>}
     */
    async deleteDocument(docId) {
      if (!docId) throw new Error("Document ID is required.");
      return request(`/documents/${encodeURIComponent(docId)}`, { method: "DELETE" });
    },

    /**
     * Perform NLP analysis, extractive summary, and clause detection
     * POST /api/documents/analyze
     * @param {string} docId - Unique document UUID
     * @param {number} summarySentences - Number of summary sentences (1-15)
     * @returns {Promise<DocumentAnalysisResponse>}
     */
    async analyzeDocument(docId, summarySentences = 4) {
      if (!docId) throw new Error("Document ID is required.");
      return request("/documents/analyze", {
        method: "POST",
        body: JSON.stringify({
          document_id: docId,
          summary_sentences: summarySentences,
        }),
      });
    },

    /**
     * Query passages across documents using TF-IDF and Cosine Similarity
     * POST /api/documents/search
     * @param {string} query - Natural language search query
     * @param {string[]|null} documentIds - Optional filter by document IDs
     * @param {number} topK - Max results (1-25)
     * @returns {Promise<SearchResponse>}
     */
    async searchDocuments(query, documentIds = null, topK = 5) {
      if (!query || !query.trim()) {
        throw new Error("Search query cannot be empty.");
      }
      return request("/documents/search", {
        method: "POST",
        body: JSON.stringify({
          query: query.trim(),
          document_ids: Array.isArray(documentIds) && documentIds.length ? documentIds : null,
          top_k: topK,
        }),
      });
    },
  };

  window.AxiomAPI = LexiScopeAPI;
  window.LexiScopeAPI = LexiScopeAPI;
})(window);
