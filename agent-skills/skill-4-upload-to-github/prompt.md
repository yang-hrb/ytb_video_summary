# Skill 4: 上传 Markdown 到 GitHub

## 适用场景
将本地生成的 Markdown 总结文件批量上传到 GitHub 指定目录。

## 环境设立（必需）
1. 在 `.env` 中配置 GitHub：
   ```bash
   GITHUB_TOKEN=your_token
   GITHUB_REPO=owner/repo
   GITHUB_BRANCH=main
   ```
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

## 输入
- `local_dir`：本地目录（含 .md 文件）
- `remote_folder`（可选）：GitHub 目标目录（默认 `reports`）
- `skip_existing`（可选）：跳过已存在文件

## 输出
- `upload_summary`：上传统计结果（成功/失败/跳过）

## 执行命令
```bash
python agent-skills/skill-4-upload-to-github/scripts/upload_markdown.py \
  --local-dir output/summaries \
  --remote-folder summaries
```
