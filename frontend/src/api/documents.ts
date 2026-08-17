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
  mime_type: string;
  file_size: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetailsResponse {
  id: string;
  filename: string;
  mime_type: string;
  file_size: number;
  status: string;
  page_count?: number;
  duration_seconds?: number;
  width?: number;
  height?: number;
  extracted_text_length?: number;
  processing_error?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  return request<DocumentUploadResponse>('/documents/upload', {
    method: 'POST',
    body: formData,
  });
}

export async function listDocuments(
  status?: string,
  limit: number = 10,
  offset: number = 0
): Promise<DocumentListItemResponse[]> {
  let query = `?limit=${limit}&offset=${offset}`;
  if (status) {
    query += `&status=${status}`;
  }
  return request<DocumentListItemResponse[]>(`/documents${query}`, {
    method: 'GET',
  });
}

export async function getDocumentDetails(documentId: string): Promise<DocumentDetailsResponse> {
  return request<DocumentDetailsResponse>(`/documents/${documentId}`, {
    method: 'GET',
  });
}

export async function deleteDocument(documentId: string): Promise<void> {
  return request<void>(`/documents/${documentId}`, {
    method: 'DELETE',
  });
}

export async function downloadDocument(documentId: string): Promise<Blob> {
  // Use custom fetch request to fetch the raw binary blob response
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
