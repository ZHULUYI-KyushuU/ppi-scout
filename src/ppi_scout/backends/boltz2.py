"""Safe local Boltz-2 command compilation and environment checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Iterable


@dataclass(frozen=True)
class BoltzDoctorResult:
    available: bool
    executable: str | None
    version_text: str | None
    gpu_text: str | None
    problems: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _probe(argv: list[str], timeout: float = 8.0) -> str | None:
    try:
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    return output or None


class Boltz2Backend:
    """Compile and optionally execute local ``boltz predict`` jobs.

    This adapter never installs dependencies and never switches MSA modes on
    failure. The caller must opt into live execution and remote MSA use.
    """

    def __init__(self, executable: str = "boltz") -> None:
        self.executable_name = executable

    def doctor(self) -> BoltzDoctorResult:
        executable = shutil.which(self.executable_name)
        problems: list[str] = []
        version_text: str | None = None
        if executable is None:
            problems.append("Boltz executable was not found on PATH.")
        else:
            version_text = _probe([executable, "--version"]) or _probe([executable, "predict", "--help"])
            if version_text is None:
                problems.append("Boltz was found but did not answer a version/help probe.")

        nvidia_smi = shutil.which("nvidia-smi")
        gpu_text = None
        if nvidia_smi:
            gpu_text = _probe(
                [
                    nvidia_smi,
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader",
                ]
            )
        if gpu_text is None:
            problems.append("No NVIDIA GPU status was detected; CPU inference may be impractical.")

        return BoltzDoctorResult(
            available=executable is not None,
            executable=executable,
            version_text=version_text,
            gpu_text=gpu_text,
            problems=tuple(problems),
        )

    @staticmethod
    def compile_input(chains: Iterable[dict[str, Any]]) -> dict[str, Any]:
        sequences: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in chains:
            chain_id = str(raw["id"]).strip()
            sequence = "".join(str(raw["sequence"]).split()).upper()
            if not chain_id or chain_id in seen:
                raise ValueError(f"Duplicate or empty chain id: {chain_id!r}")
            if not sequence or any(residue not in "ACDEFGHIKLMNPQRSTVWYX" for residue in sequence):
                raise ValueError(f"Chain {chain_id} contains an empty or invalid protein sequence.")
            seen.add(chain_id)
            protein: dict[str, Any] = {"id": chain_id, "sequence": sequence}
            msa_mode = raw.get("msa", "empty")
            if msa_mode == "empty":
                protein["msa"] = "empty"
            elif msa_mode in (None, "remote"):
                pass
            else:
                protein["msa"] = str(msa_mode)
            sequences.append({"protein": protein})
        if len(sequences) < 2:
            raise ValueError("A protein interaction job requires at least two chains.")
        return {"version": 1, "sequences": sequences}

    @staticmethod
    def write_input(payload: dict[str, Any], destination: Path) -> Path:
        """Write JSON syntax to a .yaml file.

        JSON is a YAML 1.2 subset and avoids a mandatory YAML dependency in the
        planner. The generated structure is also easy to audit and hash.
        """

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return destination

    def command(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        remote_msa: bool = False,
        output_format: str = "pdb",
        extra_args: Iterable[str] = (),
    ) -> list[str]:
        executable = shutil.which(self.executable_name) or self.executable_name
        argv = [
            executable,
            "predict",
            str(input_path),
            "--out_dir",
            str(output_dir),
            "--output_format",
            output_format,
        ]
        if remote_msa:
            argv.append("--use_msa_server")
        argv.extend(str(arg) for arg in extra_args)
        return argv

    def run(
        self,
        argv: list[str],
        *,
        live: bool = False,
        log_path: Path | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        if not live:
            return {"status": "dry_run", "argv": argv}
        if shutil.which(argv[0]) is None and not Path(argv[0]).exists():
            raise RuntimeError("Boltz is unavailable. Run `ppi-scout doctor` before live execution.")
        if stream:
            process = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            output_parts: list[str] = []
            try:
                if process.stdout is not None:
                    for line in process.stdout:
                        output_parts.append(line)
                        print(line, end="", file=sys.stderr, flush=True)
                returncode = process.wait()
            except KeyboardInterrupt:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise
            stdout = "".join(output_parts)
            stderr = ""
        else:
            completed = subprocess.run(argv, check=False, capture_output=True, text=True)
            returncode = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        if log_path is not None:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(
                json.dumps(
                    {
                        "argv": argv,
                        "returncode": returncode,
                        "stdout": stdout,
                        "stderr": stderr,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        if returncode != 0:
            raise RuntimeError(f"Boltz failed with exit code {returncode}; inspect the run log.")
        return {"status": "complete", "argv": argv, "returncode": returncode}
