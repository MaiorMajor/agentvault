#!/usr/bin/env python3
"""
_shared/secrets.py — Helper centralizado de secrets para skills Python.

Carrega os secrets de 50_infra/secrets/.env (encriptado via dotenvx).
Requer DOTENV_PRIVATE_KEY definido como variável de ambiente do sistema
(definida uma vez por device, permanentemente).

Uso nos skills:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "_shared"))
    import secrets as vault_secrets
    vault_secrets.load()

    # Ou com fallback explícito para .env local:
    vault_secrets.load(skill_dir=Path(__file__).parent)
"""

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional


def _find_dotenvx() -> str:
    """Localiza o executável dotenvx (lida com dotenvx.cmd no Windows)."""
    for name in ("dotenvx", "dotenvx.cmd"):
        found = shutil.which(name)
        if found:
            return found
    return "dotenvx"  # fallback — falhará com FileNotFoundError se não existir


def _find_vault_root() -> Path:
    """Sobe na hierarquia até encontrar a raiz do vault (directório com 99_meta/)."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "99_meta").exists():
            return parent
    # Fallback: 4 níveis acima de _shared/ (skills/_shared/ → skills/ → 50_infra/ → vault/)
    return Path(__file__).resolve().parents[3]


def _bootstrap_dotenv_private_key(verbose: bool = False) -> None:
    """Load DOTENV_PRIVATE_KEY from a local per-device env file when absent."""
    if os.environ.get("DOTENV_PRIVATE_KEY"):
        return

    candidates = []
    configured = os.environ.get("VAULT_SECRETS_FILE")
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.append(Path.home() / ".vault-secrets.env")

    for env_file in candidates:
        if not env_file.exists():
            continue

        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                if key == "DOTENV_PRIVATE_KEY" and value:
                    os.environ[key] = value
                    if verbose:
                        print(f"[secrets] ok: DOTENV_PRIVATE_KEY carregada de {env_file}")
                    return
        except OSError as e:
            if verbose:
                print(f"[secrets] aviso: nao foi possivel ler {env_file}: {e}", file=sys.stderr)


def load(skill_dir: Optional[Path] = None, verbose: bool = False) -> bool:
    """
    Carrega secrets no os.environ do processo actual.

    Estratégia (por ordem de prioridade):
    1. 50_infra/secrets/.env encriptado, via dotenvx subprocess
    2. Fallback: skill_dir/.env plain-text (compatibilidade com scripts legados)

    Args:
        skill_dir: Path para a pasta do skill (usado só no fallback).
        verbose:   Se True, imprime mensagens de diagnóstico.

    Returns:
        True  — carregou do ficheiro centralizado encriptado.
        False — usou fallback (ou não encontrou nada).
    """
    import subprocess

    _bootstrap_dotenv_private_key(verbose=verbose)

    vault = _find_vault_root()
    central = vault / "50_infra" / "secrets" / ".env"

    if central.exists():
        try:
            # Invoca dotenvx para desencriptar e injectar no subprocess Python.
            # DOTENV_PRIVATE_KEY precisa de estar definido no ambiente do sistema.
            dotenvx = _find_dotenvx()
            result = subprocess.run(
                [
                    dotenvx, "run",
                    "-f", str(central),
                    "--",
                    sys.executable, "-c",
                    "import os, json; print(json.dumps(dict(os.environ)))",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=15,
            )

            if result.returncode == 0:
                # A última linha do stdout deve ser o JSON do env
                json_lines = [l for l in result.stdout.strip().splitlines()
                              if l.strip().startswith("{")]
                if json_lines:
                    env_snapshot = json.loads(json_lines[-1])
                    injected = 0
                    skipped_encrypted = 0
                    for k, v in env_snapshot.items():
                        if isinstance(v, str) and v.startswith("encrypted:"):
                            skipped_encrypted += 1
                            continue
                        if k not in os.environ:
                            os.environ[k] = v
                            injected += 1
                    if verbose:
                        suffix = f", {skipped_encrypted} encrypted ignoradas" if skipped_encrypted else ""
                        print(f"[secrets] ok: {injected} vars carregadas de {central.name}{suffix}")
                    if skipped_encrypted:
                        print(
                            "[secrets] ERRO: secrets encriptados nao foram desencriptados. "
                            "Verifica DOTENV_PRIVATE_KEY.",
                            file=sys.stderr,
                        )
                    else:
                        return True
            else:
                stderr = result.stderr.strip()
                print(f"[secrets] ERRO: dotenvx falhou — {stderr[:200]}", file=sys.stderr)
                print("[secrets] Verifica se DOTENV_PRIVATE_KEY está definida no sistema.", file=sys.stderr)

        except FileNotFoundError:
            print("[secrets] ERRO: dotenvx não encontrado no PATH.", file=sys.stderr)
            print("[secrets] Instalar: npm install -g @dotenvx/dotenvx", file=sys.stderr)
        except Exception as e:
            print(f"[secrets] ERRO: falhou com excepção — {e}", file=sys.stderr)

    # ── Fallback: .env plain-text na pasta do skill ───────────────────────────
    if skill_dir:
        local_env = Path(skill_dir) / ".env"
        if local_env.exists():
            _load_plain_env(local_env)
            print(f"[secrets] fallback: a usar {local_env} (plain-text)", file=sys.stderr)
            return False

    print("[secrets] ERRO: nenhum .env encontrado — secrets não carregados.", file=sys.stderr)
    return False


def _load_plain_env(env_file: Path) -> None:
    """Lê um .env plain-text e injeta no os.environ (sem sobrescrever)."""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value
