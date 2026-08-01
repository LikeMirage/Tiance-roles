# Tiance Roles

天策官方在线角色仓库。普通天策客户端通过 GitHub Pages 读取市场索引，不需要安装 Git。

当前没有经过批准的公开角色，因此市场以合法空索引发布。仓库不会从任何用户的 `Data/roles` 自动收集内容。

## 角色包结构

```text
roles/<role-id>/
├─ manifest.json
├─ profile.json
├─ model.json
├─ generation.json
├─ prompt.json
├─ response.json
├─ context.json
├─ memory.json
└─ tools.json
```

角色目录只允许以上九个 JSON 文件。`.Tiance`、会话、状态、缓存、日志、脚本、附件、凭据、用户记忆和本机绝对路径不得进入仓库或角色包。

## 发布流程

`python scripts/build_market.py` 会验证所有角色，生成固定版本 ZIP、真实大小、SHA256 和 `dist/index.json`。构建使用稳定排序与固定 ZIP 元数据，同一提交可以重复得到相同产物。

推送 `main` 后，GitHub Actions 使用与 Tiance Themes 相同的 Pages 流程发布 `dist`。市场地址为：

https://likemirage.github.io/Tiance-roles

每个角色必须由内容所有者明确批准公开，并在 `manifest.json` 中声明自己的许可证；仓库基础设施不替角色作者选择内容许可证。
