import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from comfyui_rocm_setup.gpu_db import GPU_DATABASE, FALLBACK_GFX, TORCH_VERSIONS
from comfyui_rocm_setup.detector import detect_gpu, get_rocm_version
from comfyui_rocm_setup.config_gen import generate_startup_script, generate_config
from comfyui_rocm_setup.health import health_check, diagnose


class TestGPUDatabase:
    def test_known_gpus_present(self):
        assert "1002:747e" in GPU_DATABASE  # RX 7800 XT
        assert "1002:73bf" in GPU_DATABASE  # RX 6900 XT

    def test_gpu_entry_has_required_fields(self):
        for pci_id, info in GPU_DATABASE.items():
            assert "name" in info
            assert "gfx_version" in info
            assert "arch" in info
            assert "vram_gb" in info
            assert "rocm_min" in info

    def test_fallback_gfx_has_architectures(self):
        for key in ["navi3", "navi2", "navi1", "unknown"]:
            assert key in FALLBACK_GFX
            assert "gfx_version" in FALLBACK_GFX[key]

    def test_torch_versions_cover_rocm_range(self):
        assert "6.1" in TORCH_VERSIONS
        assert "6.3" in TORCH_VERSIONS
        for ver, pkg in TORCH_VERSIONS.items():
            assert "torch" in pkg


class TestDetector:
    @patch("comfyui_rocm_setup.detector._run")
    def test_detect_gpu_known(self, mock_run):
        mock_run.return_value = "03:00.0 VGA compatible controller [0300]: Advanced Micro Devices, Inc. [AMD/ATI] Navi 32 [Radeon RX 7700 XT / 7800 XT] [1002:747e] (rev c8)"
        gpu = detect_gpu()
        assert gpu is not None
        assert gpu["pci_id"] == "1002:747e"
        assert gpu["name"] == "RX 7800 XT"
        assert gpu["arch"] == "gfx1101"
        assert gpu["vram_gb"] == 16

    @patch("comfyui_rocm_setup.detector._run")
    def test_detect_gpu_no_amd(self, mock_run):
        mock_run.return_value = "00:02.0 VGA compatible controller [0300]: Intel Corporation UHD Graphics [8086:9bc4]"
        gpu = detect_gpu()
        assert gpu is None

    @patch("comfyui_rocm_setup.detector._run")
    def test_detect_gpu_unknown_amd(self, mock_run):
        mock_run.return_value = "03:00.0 VGA compatible controller [0300]: Advanced Micro Devices, Inc. [AMD/ATI] Some Future GPU [1002:abcd] (rev 01)"
        gpu = detect_gpu()
        assert gpu is not None
        assert gpu["pci_id"] == "1002:abcd"
        assert "fallback" in gpu
        assert gpu["fallback"] is True

    @patch("comfyui_rocm_setup.detector._run")
    def test_get_rocm_version_from_pacman(self, mock_run):
        mock_run.return_value = "rocm-core 7.2.4-1.1"
        ver = get_rocm_version()
        assert ver == "7.2.4"

    @patch("comfyui_rocm_setup.detector._run")
    def test_get_rocm_version_not_found(self, mock_run):
        mock_run.return_value = ""
        with patch("comfyui_rocm_setup.detector.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            ver = get_rocm_version()
            assert ver is None


class TestConfigGen:
    def test_generate_startup_script(self, tmp_path):
        env_vars = {"HSA_OVERRIDE_GFX_VERSION": "11.0.0", "HIP_VISIBLE_DEVICES": "0"}
        (tmp_path / ".venv" / "bin").mkdir(parents=True)
        (tmp_path / ".venv" / "bin" / "python3").write_text("#!/bin/bash")
        script = generate_startup_script(tmp_path, env_vars, port=8188)
        assert script.exists()
        content = script.read_text()
        assert "HSA_OVERRIDE_GFX_VERSION=11.0.0" in content
        assert "HIP_VISIBLE_DEVICES=0" in content
        assert "8188" in content
        assert script.stat().st_mode & 0o111

    def test_generate_config(self, tmp_path):
        gpu = {"name": "RX 7800 XT", "arch": "gfx1101", "vram_gb": 16, "gfx_version": "11.0.0"}
        config = generate_config(tmp_path, gpu, "6.3")
        assert config.exists()
        content = config.read_text()
        assert "RX 7800 XT" in content
        assert "gfx1101" in content
        assert "16 GB" in content

    def test_generate_config_low_vram(self, tmp_path):
        gpu = {"name": "RX 6700 XT", "arch": "gfx1031", "vram_gb": 8, "gfx_version": "10.3.0"}
        config = generate_config(tmp_path, gpu, "5.7")
        content = config.read_text()
        assert "8 GB" in content


class TestHealth:
    def test_health_check_returns_dict(self):
        results = health_check()
        assert "GPU" in results
        assert "ROCm" in results
        assert "PyTorch" in results
        assert "ComfyUI" in results
        for category, items in results.items():
            assert isinstance(items, list)

    def test_diagnose_returns_list(self):
        issues = diagnose()
        assert isinstance(issues, list)