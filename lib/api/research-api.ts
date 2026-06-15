import { apiClient } from '@/lib/api-client'

interface ApiResult<T> {
  data: T | null
  error: string | null
  isMock: boolean
}

async function safeFetch<T>(fn: () => Promise<{ data: T }>): Promise<ApiResult<T>> {
  try {
    const res = await fn()
    return { data: res.data, error: null, isMock: false }
  } catch (err: any) {
    return { data: null, error: err?.response?.data?.detail || err.message || 'Request failed', isMock: true }
  }
}

export async function fetchResearchOutputs(projectId: string): Promise<ApiResult<any>> {
  return safeFetch(() => apiClient.getProjectResearchOutputs(projectId))
}

export async function fetchPapers(projectId: string): Promise<ApiResult<any>> {
  const result = await fetchResearchOutputs(projectId)
  if (result.data?.papers) {
    return { data: result.data.papers, error: null, isMock: false }
  }
  return { data: null, error: null, isMock: true }
}

export async function fetchGapAnalysis(projectId: string): Promise<ApiResult<any>> {
  const result = await fetchResearchOutputs(projectId)
  if (result.data?.research_gaps) {
    return { data: result.data.research_gaps, error: null, isMock: false }
  }
  return { data: null, error: null, isMock: true }
}

export async function fetchNovelDirections(projectId: string): Promise<ApiResult<any>> {
  const result = await fetchResearchOutputs(projectId)
  if (result.data?.novel_directions) {
    return { data: result.data.novel_directions, error: null, isMock: false }
  }
  return { data: null, error: null, isMock: true }
}

export async function fetchLiteratureReview(projectId: string): Promise<ApiResult<any>> {
  return fetchResearchOutputs(projectId)
}

export async function fetchReport(projectId: string): Promise<ApiResult<any>> {
  const result = await fetchResearchOutputs(projectId)
  if (result.data?.report) {
    return { data: result.data.report, error: null, isMock: false }
  }
  return { data: null, error: null, isMock: true }
}
