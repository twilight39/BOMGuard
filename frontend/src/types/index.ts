export interface Bom {
  id: number
  name: string
  status: string
  totalParts: number
}

export interface ScanResult {
  partId: number
  cas: string
  regulation: string
  hitType: string
  riskScore: number
  severity: string
}
