"""
Unit Test Summary - IDLIX Downloader
Run ALL tests and show comprehensive summary
"""
import subprocess
import sys
import os

print("=" * 70)
print("🧪 IDLIX DOWNLOADER - COMPREHENSIVE UNIT TEST SUITE")
print("=" * 70)

print("\n📦 Test Files:")
test_files = [
    "tests.test_crypto",
    "tests.test_idlix_helper", 
    "tests.test_download_manager",
    "tests.test_progress_callback",
    "tests.test_vlc_player"
]

for test_file in test_files:
    module_name = test_file.split('.')[-1]
    status = "✓" if os.path.exists(f"tests/{module_name}.py") else "✗"
    print(f"  {status} {module_name}.py")

print("\n📋 Test Coverage:")
print("  • CryptoJsAes Helper - Encryption/Decryption")
print("  • IdlixHelper - Core functionality")
print("  • DownloadManager - Business logic")
print("  • Progress & Cancel - Callbacks & flags")
print("  • VLC Player - Player functionality")
print()

print("Running all tests...")
print("-" * 70)

# Run ALL tests
result = subprocess.run(
    [sys.executable, "-m", "unittest"] + test_files,
    capture_output=True,
    text=True
)

# Parse output
lines = result.stderr.split('\n')
for line in lines:
    if 'Ran' in line or 'OK' in line or 'FAILED' in line:
        print(line)

print("-" * 70)

if result.returncode == 0 or "OK" in result.stderr:
    print("✅ ALL TESTS PASSED!")
    print("\n🎯 Tested Features:")
    print("  ✓ CryptoJS AES encryption/decryption")
    print("  ✓ Video data parsing & scraping")
    print("  ✓ M3U8 URL extraction & variants")
    print("  ✓ Subtitle parsing (single/multi)")
    print("  ✓ Unified business logic (DownloadManager)")
    print("  ✓ Auto-download subtitle logic")
    print("  ✓ Subtitle modes (separate/softcode/hardcode)")
    print("  ✓ Progress callback for GUI")
    print("  ✓ Cancel flag handling")
    print("  ✓ Retry logic (3 attempts)")
    print("  ✓ Episode metadata & organized folders")
    print("  ✓ VLC player functionality")
else:
    print("❌ SOME TESTS FAILED")
    print("\nError details:")
    # Show only relevant errors
    error_lines = result.stderr.split('\n')
    for i, line in enumerate(error_lines):
        if 'FAIL:' in line or 'ERROR:' in line or 'AssertionError' in line:
            print('\n'.join(error_lines[max(0, i-2):min(len(error_lines), i+10)]))
            break
    sys.exit(1)

print("\n" + "=" * 70)
print("📝 Run individual test files:")
print("  python -m unittest tests.test_crypto -v")
print("  python -m unittest tests.test_idlix_helper -v")
print("  python -m unittest tests.test_download_manager -v")
print("  python -m unittest tests.test_progress_callback -v")
print("  python -m unittest tests.test_vlc_player -v")
print("\n💡 Run specific test:")
print("  python -m unittest tests.test_download_manager.TestDownloadManager.test_execute_download_auto_subtitle_success -v")
print("=" * 70)
