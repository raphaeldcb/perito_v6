#!/usr/bin/env python3
"""
Wave 3: Worker Health & Continuous Processing
Monitors worker polling and processes test jobs
"""
import asyncio
import time
import json
import subprocess
import re
from datetime import datetime
from pathlib import Path
from statistics import mean, median

class WorkerHealthMonitor:
    def __init__(self):
        self.results_dir = Path("wave3_results")
        self.results_dir.mkdir(exist_ok=True)

        self.log_file = self.results_dir / "worker_health.log"
        self.jobs_submitted = []
        self.jobs_completed = []
        self.start_time = None

    def log(self, msg: str):
        """Log to file and stdout"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {msg}"
        print(log_msg)
        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")

    async def run(self):
        """Execute worker health test"""
        self.start_time = time.time()
        self.log("=" * 60)
        self.log("🚀 Wave 3: Worker Health & Continuous Processing")
        self.log("=" * 60)

        try:
            # Check worker logs
            self.log("\n📊 Checking worker logs...")
            self._check_worker_logs()

            # Submit test jobs
            self.log("\n📤 Submitting test jobs...")
            await self._submit_test_jobs()

            # Monitor processing
            self.log("\n⏳ Monitoring job completion...")
            await self._monitor_jobs()

            # Analyze results
            self._analyze_results()

        except Exception as e:
            self.log(f"❌ Error: {e}")

    def _check_worker_logs(self):
        """Extract polling patterns from worker logs"""
        try:
            # Get fake-worker logs
            result = subprocess.run(
                ["docker", "logs", "--tail", "100", "perito-v6-fake-worker"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logs = result.stdout
                # Look for polling messages
                poll_lines = [line for line in logs.split("\n") if "Polling" in line or "polling" in line]

                if poll_lines:
                    self.log(f"✓ Found {len(poll_lines)} polling entries in fake-worker")
                    # Extract timestamps
                    timestamps = []
                    for line in poll_lines[:10]:
                        # Try to extract timestamp (format varies)
                        match = re.search(r'(\d{2}):(\d{2}):(\d{2})', line)
                        if match:
                            timestamps.append(match.group(0))

                    if timestamps:
                        self.log(f"  Sample polling times: {', '.join(timestamps)}")

            # Get laudo-worker logs
            result = subprocess.run(
                ["docker", "logs", "--tail", "100", "perito-v6-laudo-worker"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logs = result.stdout
                poll_lines = [line for line in logs.split("\n") if "Polling" in line or "polling" in line]

                if poll_lines:
                    self.log(f"✓ Found {len(poll_lines)} polling entries in laudo-worker")

        except Exception as e:
            self.log(f"⚠️  Could not read worker logs: {e}")

    async def _submit_test_jobs(self):
        """Submit test jobs to fake-detection endpoint"""
        import aiohttp
        from PIL import Image
        import io

        # Create test image
        test_img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        img_bytes = io.BytesIO()
        test_img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        async with aiohttp.ClientSession() as session:
            for i in range(10):
                try:
                    # Reset image bytes for each submission
                    img_bytes.seek(0)

                    submit_time = time.time()
                    async with session.post(
                        "http://localhost:8000/api/v1/fake-detection/analyze",
                        data={"file": img_bytes},
                        headers={"Authorization": "Bearer test-token"},
                        timeout=5
                    ) as resp:
                        if resp.status == 202:
                            data = await resp.json()
                            job_id = data.get("job_id")
                            self.jobs_submitted.append({
                                "id": job_id,
                                "submit_time": submit_time,
                                "status": "pending"
                            })
                            self.log(f"  ✓ Job {i+1}/10 submitted: {job_id}")
                        else:
                            self.log(f"  ❌ Job {i+1} submit failed: {resp.status}")

                except Exception as e:
                    self.log(f"  ⚠️  Job {i+1} error: {e}")

        self.log(f"✓ Submitted {len(self.jobs_submitted)} jobs")

    async def _monitor_jobs(self):
        """Poll jobs until completion"""
        import aiohttp

        timeout = 120  # 2 minutes max
        start_time = time.time()
        poll_interval = 2  # seconds

        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < timeout:
                pending = sum(1 for j in self.jobs_submitted if j['status'] == 'pending')

                if pending == 0:
                    self.log("✓ All jobs completed!")
                    break

                self.log(f"  Pending: {pending}/{len(self.jobs_submitted)}")

                # Poll each job
                for job in self.jobs_submitted:
                    if job['status'] == 'pending':
                        try:
                            async with session.get(
                                f"http://localhost:8000/api/v1/jobs/{job['id']}/status",
                                headers={"Authorization": "Bearer test-token"},
                                timeout=5
                            ) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    if data.get('status') == 'concluido':
                                        job['status'] = 'completed'
                                        job['completion_time'] = time.time()
                                        self.jobs_completed.append(job)

                        except Exception as e:
                            self.log(f"    ⚠️  Poll error for {job['id']}: {e}")

                await asyncio.sleep(poll_interval)

    def _analyze_results(self):
        """Analyze completion times and success rate"""
        self.log("\n" + "=" * 60)
        self.log("📈 Wave 3 Results")
        self.log("=" * 60)

        total = len(self.jobs_submitted)
        completed = len(self.jobs_completed)
        success_rate = (completed / total * 100) if total > 0 else 0

        self.log(f"Jobs submitted: {total}")
        self.log(f"Jobs completed: {completed}")
        self.log(f"Jobs pending: {total - completed}")
        self.log(f"Success rate: {success_rate:.1f}%")

        if self.jobs_completed:
            latencies = [
                j['completion_time'] - j['submit_time']
                for j in self.jobs_completed
            ]

            avg_latency = mean(latencies)
            median_latency = median(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)

            self.log(f"\nCompletion latencies:")
            self.log(f"  Min: {min_latency:.2f}s")
            self.log(f"  Max: {max_latency:.2f}s")
            self.log(f"  Mean: {avg_latency:.2f}s")
            self.log(f"  Median: {median_latency:.2f}s")

        # Save metrics
        self._save_metrics(success_rate)

    def _save_metrics(self, success_rate: float):
        """Save metrics to JSON"""
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_duration_sec": time.time() - self.start_time,
            "jobs_submitted": len(self.jobs_submitted),
            "jobs_completed": len(self.jobs_completed),
            "success_rate_percent": success_rate,
            "completion_latencies": {}
        }

        if self.jobs_completed:
            latencies = [
                j['completion_time'] - j['submit_time']
                for j in self.jobs_completed
            ]
            metrics["completion_latencies"] = {
                "min_sec": min(latencies),
                "max_sec": max(latencies),
                "mean_sec": mean(latencies),
                "median_sec": median(latencies)
            }

        filepath = self.results_dir / "metrics.json"
        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2)
        self.log(f"\n✓ Metrics saved to {filepath}")

async def main():
    monitor = WorkerHealthMonitor()
    await monitor.run()

if __name__ == "__main__":
    asyncio.run(main())
