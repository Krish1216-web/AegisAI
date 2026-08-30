import { request } from './client';

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  mime_type: string;
  file_size: number;
  status: string;
  created_at: string;
}

export interface DocumentListItemResponse {
  id: string;
  filename: string;
  original_filename?: string;
  mime_type: string;
  file_size: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetailsResponse {
  id: string;
  filename: string;
  original_filename?: string;
  mime_type: string;
  file_extension?: string;
  file_size: number;
  status: string;
  page_count?: number;
  duration_seconds?: number;
  width?: number;
  height?: number;
  extracted_text_length?: number;
  processing_error?: string;
  meta_data?: Record<string, any>;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface DocumentStatusResponse {
  id: string;
  status: string;
  processing_error?: string;
  page_count?: number;
  extracted_text_length?: number;
  updated_at: string;
  total_chunks: number;
  processed_chunks: number;
  failed_chunks: number;
  embedding_model?: string;
  progress: number;
}

export interface DocumentChunkResponse {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  token_count: number;
  character_count: number;
  page_number?: number;
  section_title?: string;
  created_at: string;
}

export interface DocumentActionResponse {
  document_id: string;
  status: string;
}

/**
 * Uploads a document via multipart/form-data to POST /api/v1/documents/upload.
 */
export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  return request<DocumentUploadResponse>('/documents/upload', {
    method: 'POST',
    body: formData,
  });
}

/**
 * Lists documents with optional status filtering and pagination via GET /api/v1/documents.
 */
export async function listDocuments(
  status?: string,
  limit: number = 50,
  offset: number = 0
): Promise<DocumentListItemResponse[]> {
  let query = `?limit=${limit}&offset=${offset}`;
  if (status && status !== 'ALL') {
    query += `&status=${encodeURIComponent(status)}`;
  }
  return request<DocumentListItemResponse[]>(`/documents${query}`, {
    method: 'GET',
  });
}

/**
 * Retrieves full document details via GET /api/v1/documents/{document_id}.
 */
export async function getDocumentDetails(documentId: string): Promise<DocumentDetailsResponse> {
  return request<DocumentDetailsResponse>(`/documents/${documentId}`, {
    method: 'GET',
  });
}

/**
 * Deletes a document record and storage file via DELETE /api/v1/documents/{document_id}.
 */
export async function deleteDocument(documentId: string): Promise<void> {
  return request<void>(`/documents/${documentId}`, {
    method: 'DELETE',
  });
}

/**
 * Safely streams the raw document file for downloading via GET /api/v1/documents/{document_id}/download.
 */
export async function downloadDocument(documentId: string): Promise<Blob> {
  const token = localStorage.getItem('aegis_access_token');
  const baseUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '') + '/api/v1';
  
  const response = await fetch(`${baseUrl}/documents/${documentId}/download`, {
    headers: {
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to download file: ${response.statusText}`);
  }

  return response.blob();
}

/**
 * Triggers background extraction and processing via POST /api/v1/documents/{document_id}/process.
 */
export async function processDocument(documentId: string): Promise<DocumentActionResponse> {
  return request<DocumentActionResponse>(`/documents/${documentId}/process`, {
    method: 'POST',
  });
}

/**
 * Retrieves real-time extraction & chunk embedding progress via GET /api/v1/documents/{document_id}/status.
 */
export async function getDocumentStatus(documentId: string): Promise<DocumentStatusResponse> {
  return request<DocumentStatusResponse>(`/documents/${documentId}/status`, {
    method: 'GET',
  });
}

/**
 * Lists the chunks of a document with pagination via GET /api/v1/documents/{document_id}/chunks.
 */
export async function listDocumentChunks(
  documentId: string,
  limit: number = 50,
  offset: number = 0
): Promise<DocumentChunkResponse[]> {
  return request<DocumentChunkResponse[]>(`/documents/${documentId}/chunks?limit=${limit}&offset=${offset}`, {
    method: 'GET',
  });
}

/**
 * Retrieves a single chunk detail with complete content via GET /api/v1/documents/{document_id}/chunks/{chunk_id}.
 */
export async function getDocumentChunk(
  documentId: string,
  chunkId: string
): Promise<DocumentChunkResponse> {
  return request<DocumentChunkResponse>(`/documents/${documentId}/chunks/${chunkId}`, {
    method: 'GET',
  });
}

/**
 * Clears existing chunks/embeddings and queues full reindexing via POST /api/v1/documents/{document_id}/reindex.
 */
export async function reindexDocument(documentId: string): Promise<DocumentActionResponse> {
  return request<DocumentActionResponse>(`/documents/${documentId}/reindex`, {
    method: 'POST',
  });
}
