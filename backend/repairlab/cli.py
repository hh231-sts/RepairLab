import argparse
import asyncio
import json

from .api import create_app
from .config import Settings
from .sandbox import DockerSandbox
from .worker import serve


def main():
    parser = argparse.ArgumentParser(prog="repairlab")
    parser.add_argument(
        "command",
        choices=[
            "worker",
            "seed",
            "export",
            "preflight",
            "import-swebench",
            "build-environment",
            "freeze-tasks",
            "check-config",
        ],
    )
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--id")
    parser.add_argument("--manifest")
    parser.add_argument("--revision")
    parser.add_argument("--output", default="data/export.json")
    args = parser.parse_args()
    if args.command == "check-config":
        config = Settings().public_model_config()
        print(json.dumps(config, ensure_ascii=False))
        if config["model_calls_enabled"] and not config["model_ready"]:
            raise SystemExit("Real model configuration incomplete: " + config["reason"])
        return
    if args.command == "worker":
        asyncio.run(serve(once=args.once))
        return

    async def command():
        app = create_app(Settings())
        async with app.router.lifespan_context(app):
            platform = app.state.platform
            if args.command == "seed":
                print(json.dumps(await platform.demo(DockerSandbox()), ensure_ascii=False))
            elif args.command == "export":
                from pathlib import Path

                Path(args.output).write_text(
                    json.dumps(platform.export(args.id), ensure_ascii=False, indent=2), "utf-8"
                )
            elif args.command == "preflight":
                from .tasks import preflight

                print(json.dumps(await preflight(platform, args.manifest, DockerSandbox()), indent=2))
            elif args.command == "import-swebench":
                from .tasks import import_swebench

                print(json.dumps(import_swebench(platform, args.manifest, args.revision), indent=2))
            elif args.command == "build-environment":
                from .tasks import build_environment

                print(json.dumps(await build_environment(platform, args.manifest, DockerSandbox()), indent=2))
            elif args.command == "freeze-tasks":
                from .tasks import freeze_selection

                print(json.dumps(freeze_selection(args.manifest), indent=2))

    asyncio.run(command())


if __name__ == "__main__":
    main()
