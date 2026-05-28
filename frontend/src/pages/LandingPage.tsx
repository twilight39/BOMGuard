import { Button } from '@/components/ui/button'

export function LandingPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-8 p-4">
      <h1 className="text-4xl font-heading font-bold">BOMGuard</h1>
      <p className="text-muted-foreground max-w-md text-center">
        Automated BOM compliance scanning against live ECHA, EPA regulations.
      </p>
      <div className="flex gap-4">
        <Button>Upload BOM</Button>
        <Button variant="secondary">Try a Sample</Button>
      </div>
    </div>
  )
}
