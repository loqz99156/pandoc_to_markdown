# lessons

- 如果模型下载任务长时间无输出、CPU 为 0、无活跃外网连接，并且 `.incomplete` 文件长时间不更新，就视为卡住；先终止旧任务，只删除卡住的 `.incomplete` 与对应 `.lock`，再重跑原命令。
