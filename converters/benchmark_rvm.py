import os
import sys
import time
import hashlib
import subprocess
import json

def calculate_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def run_rvm_poc():
    rvm_input = os.path.abspath(r"converters\rvmsharp_repo\TestSamples\Huldra\WD1-PSUP.RVM")
    attr_input = os.path.abspath(r"converters\rvmsharp_repo\TestSamples\Huldra\WD1-PSUP.txt")
    output_dir = os.path.abspath(r"converters\poc_output_rvm")
    os.makedirs(output_dir, exist_ok=True)
    
    dotnet_exe = os.path.expanduser(r"~\.dotnet\dotnet.exe")
    rvmsharp_dll = os.path.abspath(r"converters\rvmsharp_repo\RvmSharp.Exe\bin\Release\net8.0\RvmSharp.Exe.dll")
    
    print(f"[*] Input RVM file: {rvm_input} ({os.path.getsize(rvm_input)} bytes)")
    print(f"[*] Input Attr file: {attr_input} ({os.path.getsize(attr_input)} bytes)")
    
    # 1. Hash original pre-conversion
    hash_pre = calculate_sha256(rvm_input)
    print(f"[*] Original RVM SHA256 (pre-conversion): {hash_pre}")
    
    output_file = os.path.join(output_dir, "WD1-PSUP.obj")
    
    cmd = [
        dotnet_exe,
        rvmsharp_dll,
        "--input", rvm_input,
        "--output", output_file,
        "--tolerance", "0.1"
    ]
    
    print(f"[*] Executing command: {' '.join(cmd)}")
    start_time = time.perf_counter()
    
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed_sec = time.perf_counter() - start_time
    
    print(f"[*] Return code: {proc.returncode}")
    if proc.stdout:
        print(f"[*] Stdout: {proc.stdout[:500]}")
    if proc.stderr:
        print(f"[!] Stderr: {proc.stderr[:500]}")
        
    # 2. Hash original post-conversion
    hash_post = calculate_sha256(rvm_input)
    print(f"[*] Original RVM SHA256 (post-conversion): {hash_post}")
    
    integrity_verified = (hash_pre == hash_post)
    print(f"[*] File integrity preserved: {integrity_verified}")
    
    # 3. Analyze generated outputs
    generated_files = []
    total_output_size = 0
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            p = os.path.join(root, file)
            size = os.path.getsize(p)
            total_output_size += size
            generated_files.append({"file": file, "size_bytes": size})
            
    print(f"[*] Generated files count: {len(generated_files)}")
    print(f"[*] Total output size: {total_output_size} bytes")
    for gf in generated_files[:10]:
        print(f"    - {gf['file']}: {gf['size_bytes']} bytes")
        
    summary = {
        "status": "SUCCESS" if proc.returncode == 0 else "FAILED",
        "input_rvm_size_bytes": os.path.getsize(rvm_input),
        "input_rvm_sha256": hash_pre,
        "integrity_preserved": integrity_verified,
        "elapsed_seconds": round(elapsed_sec, 3),
        "generated_files_count": len(generated_files),
        "total_output_size_bytes": total_output_size,
        "output_files": generated_files
    }
    
    with open(os.path.join(output_dir, "benchmark_report.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        
    print(f"[*] Benchmark report written to {os.path.join(output_dir, 'benchmark_report.json')}")

if __name__ == "__main__":
    run_rvm_poc()
