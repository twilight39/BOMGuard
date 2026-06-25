export interface Bom {
  id: number
  name: string
  description?: string | null
  sourceType: string
  fileFormat?: string | null
  totalParts: number
  complianceStatus: string
  hitCount?: number
  userId?: string | null
  createdAt?: string | null
}

export interface BomPart {
  id: number
  lineNumber?: number | null
  partNumber: string
  description?: string | null
  manufacturer?: string | null
  supplier?: string | null
  quantity: number
  unit: string
  casNumbers?: string | null
}

export interface BomDetail extends Bom {
  parts: BomPart[]
}

export interface ScanResult {
  id: number
  bomId?: number | null
  partId?: number | null
  partNumber?: string | null
  partDescription?: string | null
  regulationId?: string | null
  casNumber?: string | null
  hitType?: string | null
  riskScore?: number | null
  severity?: string | null
  mlRiskScore?: number | null
  mlRiskTier?: string | null
  details?: Record<string, unknown> | null
  createdAt?: string | null
}
