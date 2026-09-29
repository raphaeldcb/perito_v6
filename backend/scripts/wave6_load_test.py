#!/usr/bin/env python3
"""
Wave 6: Load Test (1000 Concurrent Jobs)
Stress tests system at scale
"""
import asyncio
import aiohttp
import time
import json
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev
from PIL import Image
import io

class LoadTest:
    def __init__(self, base_url: str = "http://localhost:8000", total_jobs: int = 1000):
        self.base_url = base_url
        self.total_jobs = total_jobs
        self.batch_size = 100
        self.inter_batch_delay = 5

        self.submit_latencies = []
        self.completion_latencies = []
        self.jobs = []
        self.failures = 0
        self.start_time = None

        self.results_dir = Path("wave6_results")
        self.results_dir.mkdir(exist_ok=True)

    def log(self, msg: str):
        """Log with timestamp"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {msg}"
        print(log_msg)

    async def run(self):
        """Execute full load test"""
        self.start_time = time.time()
        self.log("=" * 70)
        self.log("🚀 Wave 6: Load Test (1000 Concurrent Jobs)")
        self.log("=" * 70)
        self.log(f"Configuration:")
        self.log(f"  Total jobs: {self.total_jobs}")
        self.log(f"  Batch size: {self.batch_size}")
        self.log(f"  Batches: {self.total_jobs // self.batch_size}")
        self.log(f"  Base URL: {self.base_url}")
        self.log()

        try:
            # Phase 1: Submit jobs
            await self._submit_jobs()

            # Phase 2: Poll for completion
            await self._poll_completion()

            # Phase 3: Analyze results
            self._analyze_results()

        except Exception as e:
            self.log(f"❌ Load test failed: {e}")
            import traceback
            traceback.print_exc()

    async def _submit_jobs(self):
        """Submit jobs in batches"""
        self.log("📤 Phase 1: Submitting Jobs")
        self.log("-" * 70)

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=100)) as session:
            for batch_num in range(0, self.total_jobs, self.batch_size):
                batch_end = min(batch_num + self.batch_size, self.total_jobs)
                batch_count = batch_end - batch_num

                batch_idx = (batch_num // self.batch_size) + 1
                num_batches = (self.total_jobs + self.batch_size - 1) // self.batch_size

                self.log(f"Batch {batch_idx}/{num_batches}: Submitting {batch_count} jobs...")

                # Create test image
                test_img = Image.new('RGB', (100, 100), color=(255, 0, 0))

                # Submit jobs in this batch
                tasks = []
                for i in range(batch_num, batch_end):
                    tasks.append(self._submit_single_job(session, test_img, i))

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Count successes
                successes = sum(1 for r in results if r and not isinstance(r, Exception))
                failures = sum(1 for r in results if isinstance(r, Exception))

                self.log(f"  ✓ Batch complete: {successes} submitted, {failures} failed")

                # Delay before next batch
                if batch_end < self.total_jobs:
                    self.log(f"  ⏳ Waiting {self.inter_batch_delay}s before next batch...")
                    await asyncio.sleep(self.inter_batch_delay)

        self.log(f"\n✓ Submit Phase Complete")
        self.log(f"  Total submitted: {len(self.jobs)}")
        self.log(f"  Total failures: {self.failures}")
        self.log()

    async def _submit_single_job(self, session, test_img, job_num):
        """Submit single job"""
        try:
            # Create image bytes
            img_bytes = io.BytesIO()
            test_img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            submit_time = time.time()

            async with session.post(
                f"{self.base_url}/api/v1/fake-detection/analyze",
                data={"file": img_bytes},
                headers={"Authorization": "Bearer test-token"},
                timeout=10
            ) as resp:
                if resp.status == 202:
                    data = await resp.json()
                    job_id = data.get("job_id")

                    self.jobs.append({
                        'id': job_id,
                        'submit_time': submit_time,
                        'status': 'pending'
                    })

                    submit_latency = time.time() - submit_time
                    self.submit_latencies.append(submit_latency)

                    return True
                else:
                    self.failures += 1
                    return False

        except Exception as e:
            self.failures += 1
            return False

    async def _poll_completion(self):
        """Poll jobs until completion"""
        self.log("📊 Phase 2: Polling for Completion")
        self.log("-" * 70)

        timeout = 300  # 5 minutes
        start_time = time.time()
        poll_interval = 2

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=50)) as session:
            while time.time() - start_time < timeout:
                pending = sum(1 for j in self.jobs if j['status'] == 'pending')

                if pending == 0:
                    self.log(f"✓ All jobs completed!")
                    break

                elapsed = int(time.time() - start_time)
                self.log(f"Elapsed: {elapsed}s | Pending: {pending}/{len(self.jobs)} | "
                       f"Completed: {len(self.jobs) - pending}")

                # Poll jobs
                tasks = []
                for job in self.jobs:
                    if job['status'] == 'pending':
                        tasks.append(self._poll_single_job(session, job))

                await asyncio.gather(*tasks, return_exceptions=True)

                await asyncio.sleep(poll_interval)

        elapsed = time.time() - start_time
        self.log(f"\n✓ Poll Phase Complete ({elapsed:.1f}s)")
        self.log()

    async def _poll_single_job(self, session, job):
        """Poll single job status"""
        try:
            async with session.get(
                f"{self.base_url}/api/v1/jobs/{job['id']}/status",
                headers={"Authorization": "Bearer test-token"},
                timeout=5
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    status = data.get('status')

                    if status == 'concluido':
                        job['status'] = 'completed'
                        job['completion_time'] = time.time()
                        latency = time.time() - job['submit_time']
                        self.completion_latencies.append(latency)

        except Exception as e:
            pass

    def _analyze_results(self):
        """Analyze results"""
        self.log("📈 Phase 3: Results Analysis")
        self.log("-" * 70)

        total = len(self.jobs)
        completed = sum(1 for j in self.jobs if j['status'] == 'completed')
        success_rate = (completed / total * 100) if total > 0 else 0

        self.log("Summary:")
        self.log(f"  Jobs submitted: {total}")
        self.log(f"  Jobs completed: {completed}")
        self.log(f"  Success rate: {success_rate:.1f}%")
        self.log()

        if self.completion_latencies:
            latencies = self.completion_latencies
            sorted_latencies = sorted(latencies)

            p95_idx = int(len(latencies) * 0.95)
            p99_idx = int(len(latencies) * 0.99)

            self.log("Completion Latency (seconds):")
            self.log(f"  Count: {len(latencies)}")
            self.log(f"  Min: {min(latencies):.2f}s")
            self.log(f"  Max: {max(latencies):.2f}s")
            self.log(f"  Mean: {mean(latencies):.2f}s")
            self.log(f"  Median: {median(latencies):.2f}s")
            self.log(f"  P95: {sorted_latencies[p95_idx]:.2f}s")
            self.log(f"  P99: {sorted_latencies[p99_idx]:.2f}s")
            if len(latencies) > 1:
                self.log(f"  StdDev: {stdev(latencies):.2f}s")
        else:
            self.log("❌ No completed jobs to analyze")

        self.log()
        if self.submit_latencies:
            self.log("Submit Latency (milliseconds):")
            self.log(f"  Mean: {mean(self.submit_latencies)*1000:.0f}ms")
            self.log(f"  P95: {sorted(self.submit_latencies)[int(len(self.submit_latencies)*0.95)]*1000:.0f}ms")

        # Success criteria
        self.log()
        self.log("✓ Success Criteria Check:")
        self.log(f"  [{'✓' if success_rate >= 95 else '✗'}] Success rate ≥95% (got {success_rate:.1f}%)")

        if self.completion_latencies:
            sorted_latencies = sorted(self.completion_latencies)
            p95 = sorted_latencies[int(len(sorted_latencies)*0.95)]
            p99 = sorted_latencies[int(len(sorted_latencies)*0.99)]
            self.log(f"  [{'✓' if p95 < 5 else '✗'}] P95 latency <5s (got {p95:.2f}s)")
            self.log(f"  [{'✓' if p99 < 10 else '✗'}] P99 latency <10s (got {p99:.2f}s)")

        # Save results
        self._save_results(success_rate)

    def _save_results(self, success_rate: float):
        """Save results to JSON"""
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "configuration": {
                "total_jobs": self.total_jobs,
                "batch_size": self.batch_size,
                "base_url": self.base_url
            },
            "summary": {
                "jobs_submitted": len(self.jobs),
                "jobs_completed": sum(1 for j in self.jobs if j['status'] == 'completed'),
                "success_rate_percent": success_rate,
                "total_duration_sec": time.time() - self.start_time
            }
        }

        if self.completion_latencies:
            sorted_latencies = sorted(self.completion_latencies)
            results["completion_latency"] = {
                "min_sec": min(self.completion_latencies),
                "max_sec": max(self.completion_latencies),
                "mean_sec": mean(self.completion_latencies),
                "median_sec": median(self.completion_latencies),
                "p95_sec": sorted_latencies[int(len(self.completion_latencies)*0.95)],
                "p99_sec": sorted_latencies[int(len(self.completion_latencies)*0.99)],
                "stdev_sec": stdev(self.completion_latencies) if len(self.completion_latencies) > 1 else 0
            }

        filepath = self.results_dir / "results.json"
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)

        self.log(f"✓ Results saved to {filepath}")

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Wave 6: Load Test")
    parser.add_argument("--jobs", type=int, default=1000, help="Total jobs to submit")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    args = parser.parse_args()

    test = LoadTest(base_url=args.url, total_jobs=args.jobs)
    await test.run()

if __name__ == "__main__":
    asyncio.run(main())
