#!/usr/bin/env python3
"""Manual end-to-end QA helper for the BOMGuard Docker Compose stack.

Run after `docker compose up --build -d` to verify the main user flows.
"""

import argparse
import sys
from urllib.parse import urljoin

import requests


class QAClient:
    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def _url(self, path: str) -> str:
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    def check_health(self) -> bool:
        """Verify the API health endpoint returns 200."""
        try:
            resp = self.session.get(self._url("/api/health"), timeout=10)
            resp.raise_for_status()
            print(f"[OK] Health: {resp.json()}")
            return True
        except Exception as exc:
            print(f"[FAIL] Health check failed: {exc}")
            return False

    def check_regulations(self) -> bool:
        """Verify regulations are seeded."""
        try:
            resp = self.session.get(self._url("/api/regulations/"), timeout=10)
            resp.raise_for_status()
            regs = resp.json()
            print(f"[OK] Regulations: {len(regs)} found")
            return len(regs) >= 5
        except Exception as exc:
            print(f"[FAIL] Regulations check failed: {exc}")
            return False

    def upload_sample_bom(self, sample_path: str = "samples/smartphone_pcb_bom.csv") -> bool:
        """Upload a sample BOM and verify it parses successfully."""
        try:
            with open(sample_path, "rb") as f:
                resp = self.session.post(
                    self._url("/api/boms/upload"),
                    files={"file": (sample_path.split("/")[-1], f, "text/csv")},
                    timeout=30,
                )
            resp.raise_for_status()
            data = resp.json()
            bom_id = data["id"]
            print(f"[OK] BOM uploaded: id={bom_id}")

            resp = self.session.post(self._url(f"/api/scan/{bom_id}"), timeout=60)
            resp.raise_for_status()
            scan = resp.json()
            print(f"[OK] Scan completed: {scan}")
            return True
        except Exception as exc:
            print(f"[FAIL] Upload/scan flow failed: {exc}")
            return False

    def check_metrics(self) -> bool:
        """Verify Prometheus metrics endpoint is reachable."""
        try:
            resp = self.session.get(self._url("/api/metrics"), timeout=10)
            resp.raise_for_status()
            print("[OK] Metrics endpoint reachable")
            return True
        except Exception as exc:
            print(f"[FAIL] Metrics check failed: {exc}")
            return False

    def check_admin_stats(self, admin_key: str | None = None) -> bool:
        """Verify admin stats endpoint."""
        headers = {}
        if admin_key:
            headers["X-Admin-API-Key"] = admin_key
        try:
            resp = self.session.get(
                self._url("/api/admin/ml/stats"), headers=headers, timeout=10
            )
            resp.raise_for_status()
            print(f"[OK] Admin stats: {resp.json()}")
            return True
        except Exception as exc:
            print(f"[FAIL] Admin stats check failed: {exc}")
            return False


def main() -> int:
    parser = argparse.ArgumentParser(description="BOMGuard manual E2E QA")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--admin-key", default=None)
    parser.add_argument("--sample", default="samples/smartphone_pcb_bom.csv")
    args = parser.parse_args()

    client = QAClient(args.base_url)
    checks = [
        client.check_health(),
        client.check_regulations(),
        client.check_metrics(),
        client.check_admin_stats(args.admin_key),
        client.upload_sample_bom(args.sample),
    ]

    passed = sum(checks)
    total = len(checks)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
