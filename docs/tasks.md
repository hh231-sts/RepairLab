# 任务包、离线导入和独立预检

本轮提供 `fixtures/repos/calculator` 与 `fixtures/tasks/clamp` 开发夹具，另有测试中临时生成的合成导入用例。它们不属于真实 SWE-bench 数据。真实任务当前未导入，正式模型实验未运行。

任务目录采用 [Harbor 官方格式](https://docs.harborframework.com/tasks/overview)：`instruction.md`、`task.toml`、`environment/`、`solution/`、`tests/test.sh`；评分脚本写 `/logs/verifier/reward.txt`。平台有独立 Docker runner，本轮未通过 Harbor CLI 执行真实任务集。

## 管理员离线导入

从 [SWE-bench Verified 官方来源](https://www.swebench.com/verified.html) 获取固定 dataset revision 的 JSON 记录和本地仓库，再准备管理员 manifest。导入器不联网下载数据、仓库、参考解或模型。

```json
{
  "rows": [{
    "instance": {
      "instance_id": "官方实例 ID",
      "repo": "pytest-dev/pytest",
      "base_commit": "仓库 commit SHA",
      "created_at": "原始创建时间",
      "problem_statement": "原始问题描述",
      "patch": "官方参考 unified diff",
      "test_patch": "官方测试 unified diff"
    },
    "repository": "REPOSITORY_ROOT 下的本地相对路径",
    "image": "已经构建的依赖环境镜像",
    "allowed_paths": ["src/"],
    "public_tests": ["tests"],
    "hidden_tests": ["tests/test_regression.py::test_case"]
  }]
}
```

`instance` 使用实际官方行，不使用上面的说明性占位值。管理员需根据历史任务确认依赖镜像、公开测试范围与隐藏评分节点；不自动假设三个仓库所有历史版本使用相同依赖。manifest 和 dataset revision 都会进入版本清单。

```bash
uv run repairlab import-swebench --manifest data/admin-input.json --revision <40位dataset-commit>
uv run repairlab build-environment --manifest <导出的任务包目录>
uv run repairlab preflight --manifest <任务包/manifest.json>
uv run repairlab freeze-tasks --manifest <导入批次/selection.json>
```

构建只能使用 `TASK_ROOT` 或 `data/task_imports` 内管理员任务包；构建阶段可能需要下载依赖。Agent 运行容器始终无网络。参考修复和 test patch 仅在管理员导入、预检或评分副本处理，不进入 Agent 仓库快照、文档索引、经验或 Skills。

## 选择和入库

仅允许 pytest、sphinx、sympy 三个仓库。按创建时间和实例 ID 排序，对实例 ID、问题文本和参考 patch 去重，记录排除原因。候选任务最多每仓库十二个；环境或预检失败时需要用新的候选批次替补，并保留已有筛选记录。不会按 Agent 成绩选择任务。

预检在真实环境同时执行公开回归与隐藏测试，检查原始版本、空补丁、已知无效补丁、参考补丁、重复参考补丁和重复原始版本，共六次。只有六项都符合预期才创建可执行工单。隐藏 test patch 与修复作用域重叠的任务拒绝自动入库，要求人工检查。预检错误保存为 `admitted:false`，不记为通过；各次预检另外保留带时间戳的历史记录。

冻结要求每仓库恰有十二个预检通过的任务。排序后划分每仓库 6 开发、3 回归、3 最终测试，生成 `frozen.json`，包含预检哈希、环境哈希、issue ID 和排除记录。不足 36 个时拒绝冻结。

## 评分

Agent 只看到 issue、固定基线、公开材料、工具和允许的公开测试。执行结束后导出最终补丁，在干净基线上应用允许范围内的变化，再加入隐藏测试覆盖层评分；隐藏层不能覆盖实现修复范围。结果绑定补丁、源快照、环境镜像和验证器哈希。补丁或验证器变化后不能复用旧结果。

公共历史任务可能在模型训练中出现。后续报告必须保留这一限制，且不将脚本化夹具通过解释为模型推理或协作收益。
