export function RegulationsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-heading font-bold">Regulations</h1>
      <div className="rounded-lg border bg-card">
        <table className="w-full text-sm">
          <thead className="border-b bg-muted">
            <tr>
              <th className="text-left px-4 py-3 font-medium">ID</th>
              <th className="text-left px-4 py-3 font-medium">Name</th>
              <th className="text-left px-4 py-3 font-medium">Authority</th>
              <th className="text-left px-4 py-3 font-medium">ML</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b">
              <td className="px-4 py-3 font-mono text-xs">eu_reach_svhc</td>
              <td className="px-4 py-3">EU REACH SVHC Candidate List</td>
              <td className="px-4 py-3 text-muted-foreground">ECHA</td>
              <td className="px-4 py-3">
                <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs">
                  disabled
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
