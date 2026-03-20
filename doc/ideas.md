- 升级log， info
- 每次batch进行一次 github上传。（但需要考虑失败的情况）
- up主的名字：去掉空格，和括号和符号，只保留中文/英文，空格用下划线代替。
- 视频的标题也要一样标准化处理。

- 输出文字改为4096 token。（默认是2000）

孙三通（大号）

summary/
├── {uploader}/
│   ├── info.json
│   ├── summary_prompt.txt
│   └── {YYYY_MM}/
│       └── {upload_date}_{uploader}_{title}.md
├── daily_summary/
│   └── {YYYY_MM}/
│       └── {YYYY-MM-DD}.md



=============================
summary/
├── {uploader}/
│   ├── info.json
│   ├── summary_prompt.txt
│   └── {YYYY_MM}/
│       └── {upload_date}_{uploader}_{title}.md

这部分看到了，没问题。非常好。

但这个没看到
├── daily_summary/
│   └── {YYYY_MM}/
│       └── {YYYY-MM-DD}.md

把这个daily放入
daily_digeset/
│  └── {YYYY_MM}/
│     └── {YYYY-MM-DD}-{timestamp:HH:MM}.md

运行完成后，也上传到github

=======================



