export interface Bom {
  id: number
  name: string
  description?: string | null
  sourceType: string
  fileFormat?: string | null
  totalParts: number
  complianceStatus: string
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
  partId: number
  cas: string
  regulation: string
  hitType: string
  riskScore: number
  severity: string
}
