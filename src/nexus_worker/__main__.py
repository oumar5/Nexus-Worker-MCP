"""Point d'entrée CLI de Nexus-Worker-MCP.

Permet de lancer le serveur via `python -m nexus_worker`
ou de diagnostiquer la configuration via `--health-check`.
"""

from __future__ import annotations

import argparse
import asyncio
import sys


def main() -> None:
    """Point d'entrée principal du CLI."""
    parser = argparse.ArgumentParser(
        prog="nexus-worker",
        description="Nexus-Worker-MCP — Serveur MCP pour la délégation de tâches LLM.",
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Vérifie la connexion au provider et affiche les informations de diagnostic.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Chemin vers le fichier .env (défaut: .env).",
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Affiche les métriques de la session en cours.",
    )

    args = parser.parse_args()

    if args.health_check:
        asyncio.run(_run_health_check(args.env_file))
    else:
        _run_server(args.env_file)


def _run_server(env_file: str) -> None:
    """Lance le serveur MCP.

    Args:
        env_file: Chemin vers le fichier .env.
    """
    from nexus_worker.config import Config
    from nexus_worker.server import NexusWorkerServer

    config = Config(env_file=env_file)
    server = NexusWorkerServer(config)
    server.run()


async def _run_health_check(env_file: str) -> None:
    """Exécute le diagnostic du provider.

    Vérifie la connexion API, le modèle, et affiche les résultats.

    Args:
        env_file: Chemin vers le fichier .env.
    """
    from nexus_worker.config import Config
    from nexus_worker.providers.factory import create_providers_from_config, list_providers

    config = Config(env_file=env_file)
    primary, fallback = create_providers_from_config(config)

    print("\n🔍 Nexus-Worker-MCP — Diagnostic\n")
    print(f"{'─' * 50}")

    # Info provider principal
    info = primary.get_info()
    print(f"  Provider:  {info.get('provider', 'unknown')}")
    print(f"  Model:     {info.get('model', 'unknown')}")
    print(f"  Endpoint:  {info.get('endpoint', 'unknown')}")
    if info.get("mode"):
        print(f"  Mode:      {info['mode']}")

    # Health check
    print(f"\n  Connexion API...", end=" ")
    try:
        is_healthy = await primary.health_check()
        if is_healthy:
            print("✅ OK")
        else:
            print("❌ Échec (le modèle n'est peut-être pas disponible)")
    except Exception as e:
        print(f"❌ Erreur: {e}")

    # Transport
    print(f"\n  Transport: {config.transport.mode}")
    if config.transport.mode == "http":
        print(f"  Host:      {config.transport.host}")
        print(f"  Port:      {config.transport.port}")

    # Outils
    from nexus_worker.prompts.engine import PromptEngine

    engine = PromptEngine(config.prompt_templates_dir)
    templates = engine.list_templates()
    print(f"  Templates: {len(templates)} ({', '.join(templates)})")

    # Fallback
    if fallback:
        print(f"\n  Fallback Provider:")
        fb_info = fallback.get_info()
        print(f"    Provider: {fb_info.get('provider', 'unknown')}")
        print(f"    Model:    {fb_info.get('model', 'unknown')}")
        print(f"    Health:   ", end="")
        try:
            fb_healthy = await fallback.health_check()
            print("✅ OK" if fb_healthy else "❌ Échec")
        except Exception:
            print("❌ Erreur")
    else:
        print(f"\n  Fallback:  Non configuré")

    # Providers disponibles
    print(f"\n  Providers disponibles: {', '.join(list_providers())}")
    print(f"{'─' * 50}\n")


if __name__ == "__main__":
    main()
