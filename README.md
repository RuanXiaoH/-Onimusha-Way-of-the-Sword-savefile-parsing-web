# 鬼武者：剑之道 · 存档阅览

本地阅览《鬼武者：剑之道》的 `data001Slot.bin`：栏位、装备、鬼之武具、鬼灯袋、御守、狛犬、幻魔杂记、Boss 与 Steam 成就。

在浏览器里提交存档即可，不会把文件传到第三方。解密和解析都在本机完成。

## 运行

需要 **Node.js 20+**、**Python 3.10+**。加密存档解密时要在网页上填写自己的 64 位 SteamID。

```bash
cd web
npm install
npm run dev
```

## 仓库内容

- `web/`：阅览页（Vite + React）
- `scripts/analyze_bin.py`：解密并打成页面用的 JSON
- `scripts/parse_save.py`、`scripts/make_display_data.py`：明文解析
- `dumps/rszoniwots.json`、`dumps/oniwots_enums.json`：解析用的类型表
- `tools/mandarin_cli/`：存档解密 CLI
