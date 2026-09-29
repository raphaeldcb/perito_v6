#!/usr/bin/env python3
"""
Wave 1: End-to-End Browser Workflow Test
Tests: Login → Fake Detection → Laudo Generation → Download
"""
import asyncio
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path

class Wave1E2ETest:
    def __init__(self, base_url: str = "http://localhost:5173"):
        self.base_url = base_url
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "workflows": {},
            "success": False
        }
        self.screenshot_dir = Path("wave1_results")
        self.screenshot_dir.mkdir(exist_ok=True)

    async def run(self):
        """Execute all E2E workflows"""
        print("🌐 Wave 1: End-to-End Browser Workflow Test")
        print(f"   Base URL: {self.base_url}")
        print()

        try:
            # Check if frontend is running
            await self._check_frontend()

            # Test 1: Login
            await self._test_login()

            # Test 2: Fake Detection
            await self._test_fake_detection()

            # Test 3: Laudo Generation
            await self._test_laudo_generation()

            # Summary
            self._print_summary()

            # Save results
            self._save_results()

        except Exception as e:
            print(f"❌ Test failed: {e}")
            self.results["error"] = str(e)
            self._save_results()

    async def _check_frontend(self):
        """Verify frontend is running"""
        import aiohttp
        print("📡 Checking frontend status...")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/") as resp:
                    if resp.status == 200:
                        print("   ✓ Frontend responding on port 5173")
                    else:
                        raise Exception(f"Frontend returned {resp.status}")
        except Exception as e:
            print(f"   ❌ Frontend not available: {e}")
            print("   💡 Start frontend: cd frontend && npm run dev")
            raise

    async def _test_login(self):
        """Test login workflow"""
        print("\n🔐 Test 1: Login Workflow")
        print("   Using agent-browser to test login...")

        start = time.time()

        try:
            # Use agent-browser to automate
            result = subprocess.run([
                "agent-browser",
                "--url", f"{self.base_url}/login",
                "--script", """
                // Find and fill email
                const emailInput = document.querySelector('input[name="email"]');
                emailInput.value = 'admin@ipcms.com.br';
                emailInput.dispatchEvent(new Event('change', { bubbles: true }));

                // Find and fill password
                const passInput = document.querySelector('input[name="password"]');
                passInput.value = 'admin123';
                passInput.dispatchEvent(new Event('change', { bubbles: true }));

                // Click login button
                document.querySelector('button[type="submit"]').click();

                // Wait for redirect
                await new Promise(r => setTimeout(r, 2000));

                // Check if on dashboard
                const isDashboard = window.location.pathname === '/dashboard';
                return { success: isDashboard, url: window.location.pathname };
                """
            ], capture_output=True, text=True, timeout=30)

            duration = time.time() - start

            if result.returncode == 0:
                print(f"   ✓ Login successful ({duration:.1f}s)")
                self.results["workflows"]["login"] = {
                    "status": "pass",
                    "duration_sec": duration
                }
            else:
                print(f"   ❌ Login failed: {result.stderr}")
                self.results["workflows"]["login"] = {
                    "status": "fail",
                    "error": result.stderr
                }

        except subprocess.TimeoutExpired:
            print("   ❌ Login test timed out")
            self.results["workflows"]["login"] = {"status": "timeout"}
        except Exception as e:
            print(f"   ⚠️  Agent-browser not available, using curl fallback")
            # Fallback: Use curl to test API directly
            await self._test_login_api()

    async def _test_login_api(self):
        """Fallback: Test login via API"""
        import aiohttp

        print("   📡 Testing login via API...")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    "http://localhost:8000/api/v1/auth/login",
                    json={"email": "admin@ipcms.com.br", "password": "admin123"},
                    timeout=10
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"   ✓ Login API successful")
                        self.results["workflows"]["login"] = {
                            "status": "pass",
                            "method": "api"
                        }
                    else:
                        print(f"   ❌ Login failed: {resp.status}")
                        self.results["workflows"]["login"] = {
                            "status": "fail",
                            "status_code": resp.status
                        }
            except Exception as e:
                print(f"   ❌ API error: {e}")
                self.results["workflows"]["login"] = {"status": "error"}

    async def _test_fake_detection(self):
        """Test fake detection workflow"""
        print("\n🖼️  Test 2: Fake Detection Workflow")
        import aiohttp
        from PIL import Image
        import io

        start = time.time()

        # Create test image
        test_img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        test_img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        try:
            async with aiohttp.ClientSession() as session:
                # Submit job
                print("   📤 Submitting fake detection job...")
                async with session.post(
                    "http://localhost:8000/api/v1/fake-detection/analyze",
                    data={"file": img_bytes},
                    headers={"Authorization": "Bearer test-token"},
                    timeout=10
                ) as resp:
                    if resp.status == 202:
                        data = await resp.json()
                        job_id = data.get("job_id")
                        print(f"   ✓ Job submitted: {job_id}")

                        # Poll for completion
                        print("   ⏳ Polling for result...")
                        result = await self._poll_job(session, job_id, "fake-detection", 30)

                        if result:
                            duration = time.time() - start
                            print(f"   ✓ Job completed ({duration:.1f}s)")
                            self.results["workflows"]["fake_detection"] = {
                                "status": "pass",
                                "job_id": job_id,
                                "duration_sec": duration
                            }
                        else:
                            print("   ❌ Job did not complete in time")
                            self.results["workflows"]["fake_detection"] = {
                                "status": "timeout",
                                "job_id": job_id
                            }
                    else:
                        print(f"   ❌ Submit failed: {resp.status}")
                        self.results["workflows"]["fake_detection"] = {
                            "status": "fail",
                            "status_code": resp.status
                        }

        except Exception as e:
            print(f"   ❌ Error: {e}")
            self.results["workflows"]["fake_detection"] = {"status": "error"}

    async def _test_laudo_generation(self):
        """Test laudo generation workflow"""
        print("\n📝 Test 3: Laudo Generation Workflow")
        import aiohttp

        start = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                # Create laudo
                print("   📤 Submitting laudo generation job...")
                laudo_data = {
                    "numero_processo": "0000001-00.2024.8.28.0001",
                    "area": "CONTABIL",
                    "tipo_pericia": "JUDICIAL",
                    "fatos": "Análise fundamentada do contrato de serviços.",
                    "quesitos": ["Houve vícios?", "Qual é o dano?"]
                }

                async with session.post(
                    "http://localhost:8000/api/v1/laudos/generate",
                    json=laudo_data,
                    headers={"Authorization": "Bearer test-token"},
                    timeout=30
                ) as resp:
                    if resp.status == 202:
                        data = await resp.json()
                        job_id = data.get("job_id")
                        print(f"   ✓ Job submitted: {job_id}")

                        # Poll for completion
                        print("   ⏳ Polling for result...")
                        result = await self._poll_job(session, job_id, "laudo-generation", 120)

                        if result:
                            duration = time.time() - start
                            print(f"   ✓ Job completed ({duration:.1f}s)")

                            # Try to download
                            print("   📥 Downloading laudo...")
                            download_ok = await self._download_laudo(session, job_id)

                            self.results["workflows"]["laudo_generation"] = {
                                "status": "pass",
                                "job_id": job_id,
                                "duration_sec": duration,
                                "download": "ok" if download_ok else "failed"
                            }
                        else:
                            print("   ❌ Job did not complete in time")
                            self.results["workflows"]["laudo_generation"] = {
                                "status": "timeout",
                                "job_id": job_id
                            }
                    else:
                        print(f"   ❌ Submit failed: {resp.status}")
                        self.results["workflows"]["laudo_generation"] = {
                            "status": "fail",
                            "status_code": resp.status
                        }

        except Exception as e:
            print(f"   ❌ Error: {e}")
            self.results["workflows"]["laudo_generation"] = {"status": "error"}

    async def _poll_job(self, session, job_id: str, job_type: str, timeout: int):
        """Poll job status until complete"""
        start = time.time()

        while time.time() - start < timeout:
            try:
                async with session.get(
                    f"http://localhost:8000/api/v1/jobs/{job_id}/status",
                    headers={"Authorization": "Bearer test-token"},
                    timeout=5
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        status = data.get("status")

                        if status == "concluido":
                            return True
                        elif status == "erro":
                            print(f"      ❌ Job error: {data.get('error')}")
                            return False

                        elapsed = time.time() - start
                        print(f"      ⏳ Status: {status} ({elapsed:.0f}s elapsed)")

            except Exception as e:
                print(f"      ⚠️  Poll error: {e}")

            await asyncio.sleep(2)

        return False

    async def _download_laudo(self, session, job_id: str):
        """Download laudo DOCX file"""
        try:
            async with session.get(
                f"http://localhost:8000/api/v1/laudos/{job_id}/download",
                headers={"Authorization": "Bearer test-token"},
                timeout=10
            ) as resp:
                if resp.status == 200:
                    # Save file
                    content = await resp.content.read()
                    filepath = self.screenshot_dir / f"laudo_{job_id}.docx"
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    print(f"      ✓ Downloaded ({len(content)} bytes)")
                    return True
        except Exception as e:
            print(f"      ❌ Download failed: {e}")

        return False

    def _print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📊 WAVE 1 SUMMARY")
        print("="*60)

        total = len(self.results["workflows"])
        passed = sum(1 for w in self.results["workflows"].values() if w.get("status") == "pass")

        for workflow, result in self.results["workflows"].items():
            status_icon = "✓" if result.get("status") == "pass" else "❌"
            print(f"{status_icon} {workflow}: {result.get('status')} ({result.get('duration_sec', 'N/A')}s)")

        print()
        print(f"Total: {passed}/{total} workflows passed")

        if passed == total:
            self.results["success"] = True
            print("✅ Wave 1: PASS")
        else:
            print("❌ Wave 1: FAIL")

    def _save_results(self):
        """Save results to JSON"""
        filepath = self.screenshot_dir / "results.json"
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n✓ Results saved to {filepath}")

async def main():
    test = Wave1E2ETest()
    await test.run()

if __name__ == "__main__":
    asyncio.run(main())
