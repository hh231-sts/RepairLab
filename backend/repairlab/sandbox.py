import asyncio
import json
import re
from pathlib import Path


class SandboxError(RuntimeError):
    pass


class DockerSandbox:
    """Only allowlisted pytest execution; no host shell, daemon socket or secret mounts."""

    async def command(self, *args: str, timeout: int = 30, allow_failure=False):
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            out, err = await asyncio.wait_for(process.communicate(), timeout)
        except FileNotFoundError as exc:
            raise SandboxError("docker executable unavailable") from exc
        except TimeoutError as exc:
            process.kill()
            await process.wait()
            raise SandboxError("docker command timeout") from exc
        if process.returncode and not allow_failure:
            raise SandboxError(err.decode(errors="replace")[-2000:])
        return process.returncode, out.decode(errors="replace"), err.decode(errors="replace")

    async def image_hash(self, image: str) -> str:
        _, out, _ = await self.command("image", "inspect", image, "--format", "{{.Id}}")
        return out.strip()

    async def inspect(self, name: str):
        code, out, _ = await self.command("inspect", name, allow_failure=True)
        return json.loads(out)[0] if code == 0 else None

    async def stop(self, name: str):
        await self.command("rm", "-f", name, allow_failure=True)

    async def test(
        self,
        workspace: Path,
        image: str,
        paths: list[str],
        action_id: str,
        timeout: int,
        verifier: Path | None = None,
        cancelled=None,
    ) -> dict:
        if not re.fullmatch(r"[a-f0-9]{16,64}", action_id):
            raise SandboxError("invalid action ID")
        name = "repairlab-" + action_id[:40]
        state = await self.inspect(name)
        if state is None:
            args = [
                "create",
                "--name",
                name,
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "128",
                "--memory",
                "512m",
                "--cpus",
                "1",
                "--log-driver",
                "json-file",
                "--log-opt",
                "max-size=8m",
                "--log-opt",
                "max-file=1",
                "--user",
                "1000:1000",
                "--tmpfs",
                "/tmp:rw,nosuid,size=64m",
                "--mount",
                f"type=bind,source={workspace.resolve()},target=/workspace,readonly",
                "--workdir",
                "/workspace",
                "--env",
                "PYTHONPATH=/workspace",
                "--env",
                "PYTHONDONTWRITEBYTECODE=1",
                "--env",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
            ]
            if verifier:
                args += ["--mount", f"type=bind,source={verifier.resolve()},target=/verifier,readonly"]
            args += [image, "python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *paths]
            await self.command(*args)
            state = await self.inspect(name)
        if state["State"]["Status"] == "created":
            await self.command("start", name)
        loop = asyncio.get_running_loop()
        start = loop.time()
        while True:
            state = await self.inspect(name)
            if not state:
                raise SandboxError("execution container lost; execution outcome uncertain")
            if state["State"]["Status"] in {"exited", "dead"}:
                _, out, err = await self.command("logs", name, allow_failure=True)
                return {
                    "exit_code": state["State"]["ExitCode"],
                    "stdout": out,
                    "stderr": err,
                    "container": name,
                    "oom": state["State"].get("OOMKilled", False),
                }
            if loop.time() - start >= timeout or (cancelled and cancelled()):
                await self.command("kill", name, allow_failure=True)
                raise SandboxError(
                    "execution cancelled" if cancelled and cancelled() else "execution timeout"
                )
            await asyncio.sleep(0.2)
