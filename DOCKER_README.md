# YouTube Playlist Summarizer - Docker Deployment Guide

一键部署 YouTube 播放列表视频摘要生成器。

## 快速开始

### 1. 准备工作

```bash
# 克隆仓库
git clone https://github.com/yang-hrb/ytb_video_summary.git
cd ytb_video_summary

# 复制环境变量配置文件
cp .env.example .env
```

### 2. 配置环境变量

编辑 `.env` 文件，配置必要的 API 密钥：

```bash
# 必填：选择一个 AI 摘要服务
SUMMARY_API=OPENROUTER  # 或 PERPLEXITY

# OpenRouter 配置（推荐）
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=tngtech/deepseek-r1t2-chimera:free

# 或 Perplexity 配置
# PERPLEXITY_API_KEY=your_perplexity_api_key_here
# PERPLEXITY_MODEL=sonar-pro

# 可选：GitHub 自动上传
GITHUB_TOKEN=your_github_personal_access_token_here
GITHUB_REPO=username/repository_name
GITHUB_BRANCH=main

# Whisper 配置
WHISPER_MODEL=base  # tiny/base/small/medium/large
WHISPER_LANGUAGE=auto  # zh/en/auto

# 摘要输出语言
SUMMARY_LANGUAGE=zh  # zh/en
```

### 3. 构建 Docker 镜像

```bash
docker-compose build
```

### 4. 运行处理播放列表

#### 方法一：使用 docker-compose（推荐）

```bash
# 设置播放列表 URL 并运行
export PLAYLIST_URL="https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID"
docker-compose run --rm youtube-playlist-summarizer
```

#### 方法二：直接使用 docker run

```bash
# 构建镜像
docker build -t ytb-playlist-summarizer .

# 运行容器
docker run --rm \
  --env-file .env \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/logs:/app/logs \
  ytb-playlist-summarizer \
  -list "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID" \
  --style detailed \
  --upload
```

#### 方法三：使用便捷脚本

```bash
# 创建并运行脚本
./run-docker.sh "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID"
```

### 5. 处理会员视频（可选）

如果播放列表包含会员专属视频：

1. 使用浏览器扩展导出 cookies：
   - Chrome: "Get cookies.txt LOCALLY" 扩展
   - Firefox: "cookies.txt" 扩展

2. 保存为项目根目录的 `cookies.txt`

3. 运行时会自动检测并使用 cookies 文件

```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/cookies.txt:/app/cookies.txt:ro \
  ytb-playlist-summarizer \
  -list "YOUR_PLAYLIST_URL" \
  --cookies /app/cookies.txt \
  --upload
```

## 输出文件

处理完成后，输出文件位于：

```
output/
├── transcripts/    # 字幕文件 (SRT 格式)
│   └── [video_id]_transcript.srt
├── summaries/      # 视频摘要（按视频 ID）
│   └── [video_id]_summary.md
└── reports/        # 带时间戳的详细报告
    └── YYYYMMDD_HHMM_[uploader]_[title].md

logs/
├── run_track.db    # 处理记录数据库
├── failures_*.txt  # 失败日志
└── youtube_summarizer_*.log  # 应用日志
```

## 高级配置

### 自定义资源限制

编辑 `docker-compose.yml`：

```yaml
deploy:
  resources:
    limits:
      cpus: '4'      # 调整 CPU 限制
      memory: 8G     # 调整内存限制
```

### 持久化数据

默认配置已映射以下目录：
- `./output` → 处理结果
- `./logs` → 日志文件

### 环境变量覆盖

```bash
# 临时覆盖环境变量
docker-compose run --rm \
  -e WHISPER_MODEL=large \
  -e SUMMARY_LANGUAGE=en \
  youtube-playlist-summarizer \
  -list "YOUR_PLAYLIST_URL"
```

## 部署到生产环境

### 部署到 VPS 服务器（如 ytb-download.yangyu.us）

#### 准备工作

1. **VPS 服务器要求**：
   - 操作系统：Ubuntu 20.04/22.04 或 CentOS 7/8
   - 内存：至少 4GB RAM（推荐 8GB）
   - 存储：至少 20GB 可用空间
   - 已安装 Docker 和 Docker Compose

2. **域名配置**：
   - 将域名 `ytb-download.yangyu.us` 的 A 记录指向你的 VPS IP 地址
   - 等待 DNS 传播（通常 5-30 分钟）

#### 步骤 1：服务器初始配置

```bash
# SSH 登录服务器
ssh root@your-server-ip

# 更新系统
apt update && apt upgrade -y

# 安装 Docker（如未安装）
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 安装 Docker Compose
apt install docker-compose -y

# 创建应用目录
mkdir -p /opt/ytb-summarizer
cd /opt/ytb-summarizer
```

#### 步骤 2：部署应用

```bash
# 克隆代码（或上传文件）
git clone https://github.com/yang-hrb/ytb_video_summary.git .

# 配置环境变量
cp .env.example .env
nano .env  # 编辑配置

# 构建镜像
docker-compose build

# 测试运行
docker-compose run --rm youtube-playlist-summarizer --help
```

#### 步骤 3：配置 Web 服务（Nginx 反向代理）

如果要通过 Web 界面访问：

```bash
# 安装 Nginx
apt install nginx -y

# 创建 Nginx 配置
cat > /etc/nginx/sites-available/ytb-summarizer << 'EOF'
server {
    listen 80;
    server_name ytb-download.yangyu.us;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ytb-download.yangyu.us;

    # SSL 证书（使用 Let's Encrypt）
    ssl_certificate /etc/letsencrypt/live/ytb-download.yangyu.us/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ytb-download.yangyu.us/privkey.pem;

    # 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 静态文件服务（输出结果）
    location /output/ {
        alias /opt/ytb-summarizer/output/;
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;
    }

    # 日志
    location /logs/ {
        alias /opt/ytb-summarizer/logs/;
        autoindex on;
        auth_basic "Restricted";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }

    # 主页（可选：添加 Web UI）
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# 启用站点
ln -s /etc/nginx/sites-available/ytb-summarizer /etc/nginx/sites-enabled/

# 测试配置
nginx -t

# 重启 Nginx
systemctl restart nginx
```

#### 步骤 4：配置 SSL 证书（HTTPS）

```bash
# 安装 Certbot
apt install certbot python3-certbot-nginx -y

# 获取 SSL 证书
certbot --nginx -d ytb-download.yangyu.us

# 验证自动续期
certbot renew --dry-run
```

#### 步骤 5：设置定时任务（可选）

自动处理特定播放列表：

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨 2 点运行）
0 2 * * * cd /opt/ytb-summarizer && docker-compose run --rm youtube-playlist-summarizer -list "YOUR_PLAYLIST_URL" --upload >> /var/log/ytb-summarizer-cron.log 2>&1
```

#### 步骤 6：监控和维护

```bash
# 查看运行日志
docker-compose logs -f

# 查看输出文件
ls -lh output/reports/

# 清理旧的临时文件
docker system prune -a -f

# 备份数据
tar -czf backup-$(date +%Y%m%d).tar.gz output/ logs/
```

### 通过 API 调用（高级）

创建简单的 Web API 服务：

```bash
# 创建 API 脚本
cat > api.py << 'EOF'
from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process_playlist():
    data = request.json
    playlist_url = data.get('playlist_url')

    if not playlist_url:
        return jsonify({'error': 'Missing playlist_url'}), 400

    # 运行 Docker 容器
    cmd = [
        'docker-compose', 'run', '--rm',
        'youtube-playlist-summarizer',
        '-list', playlist_url,
        '--upload'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    return jsonify({
        'status': 'success' if result.returncode == 0 else 'error',
        'output': result.stdout,
        'error': result.stderr
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
EOF

# 运行 API（在后台）
python3 api.py &
```

调用 API：

```bash
curl -X POST https://ytb-download.yangyu.us/process \
  -H "Content-Type: application/json" \
  -d '{"playlist_url": "YOUR_PLAYLIST_URL"}'
```

## 故障排查

### 常见问题

1. **FFmpeg 未找到**
   ```bash
   # 进入容器检查
   docker-compose run --rm youtube-playlist-summarizer sh
   which ffmpeg
   ```

2. **内存不足**
   ```bash
   # 增加 Docker 内存限制
   # 编辑 docker-compose.yml 中的 memory 值
   ```

3. **权限问题**
   ```bash
   # 修复输出目录权限
   sudo chown -R $(id -u):$(id -g) output/ logs/
   ```

4. **API 密钥无效**
   ```bash
   # 验证 .env 文件配置
   cat .env | grep API_KEY
   ```

### 查看日志

```bash
# Docker 容器日志
docker-compose logs -f

# 应用日志
tail -f logs/youtube_summarizer_*.log

# 失败记录
cat logs/failures_*.txt
```

## 性能优化

### 使用更快的 Whisper 模型

```bash
# 在 .env 中配置
WHISPER_MODEL=tiny  # 最快，精度较低
WHISPER_MODEL=base  # 平衡（推荐）
WHISPER_MODEL=large # 最慢，精度最高
```

### 并行处理多个播放列表

```bash
# 同时处理多个播放列表
for url in $(cat playlists.txt); do
  docker-compose run --rm -d youtube-playlist-summarizer -list "$url" --upload
done
```

### 缓存和复用

Docker 镜像会缓存 Whisper 模型，首次运行后后续处理会更快。

## 安全建议

1. **保护 API 密钥**：不要将 `.env` 文件提交到 Git
2. **使用 HTTPS**：生产环境必须使用 SSL 证书
3. **限制访问**：使用防火墙限制访问
4. **定期更新**：保持 Docker 镜像和依赖更新

```bash
# 定期更新镜像
docker-compose pull
docker-compose build --no-cache
```

## 资源和支持

- **项目仓库**：https://github.com/yang-hrb/ytb_video_summary
- **问题反馈**：https://github.com/yang-hrb/ytb_video_summary/issues
- **文档**：查看项目根目录的 README.md 和 CLAUDE.md

## 许可证

根据项目许可证使用。
