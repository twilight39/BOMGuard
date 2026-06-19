# Plan: Frontend Test Suite

## Goal
Add automated testing to the React frontend.

## Scope
- `frontend/package.json` (dev dependencies)
- `frontend/src/**/*.test.ts(x)`
- CI workflow

## Tasks
1. [ ] **Install Vitest**: `npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom @vitejs/plugin-react`.
2. [ ] **Config**: Add `vitest.config.ts` extending `vite.config.ts` with `environment: 'jsdom'` and `@/` alias.
3. [ ] **Test utilities**: Create `frontend/src/test/setup.ts` importing `@testing-library/jest-dom/vitest`.
4. [ ] **Component tests**:
   - `BomUpload.test.tsx` — drag-drop, file validation, API call.
   - `ChatInterface.test.tsx` — message send, markdown render, thread switch.
   - `ScanSummaryModal.test.tsx` — risk badge render, close action.
5. [ ] **Hook tests**:
   - `useApi.test.ts` — request/response/error states.
6. [ ] **CI update**: Add `npm run test` to `.github/workflows/ci.yml` under `test-frontend` job.
7. [ ] **Coverage**: Set threshold at 60% lines; report in CI.

## Dependencies
- `feat/frontend-page-components` (or at least stable component APIs)

## Outcome
Frontend has unit tests for critical components and hooks; CI fails on test breakage.
