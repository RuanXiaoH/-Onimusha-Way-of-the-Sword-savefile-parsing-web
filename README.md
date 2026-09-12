# 鬼武者：剑之道 · 存档阅览

本地阅览《鬼武者：剑之道》的 `data001Slot.bin`：栏位、装备、鬼之武具、鬼灯袋、御守、狛犬、幻魔杂记、Boss 与 Steam 成就。

在浏览器里提交存档即可，不会把文件传到第三方。解密和解析都在本机完成。

## 运行

需要 **Node.js 20+**、**Python 3.10+**。解密加密存档时还要填自己的 SteamID。

```bash
cd web
npm install
npm run dev
```

浏览器打开 <http://127.0.0.1:5177/>，提交 Steam 云存档里的 `data001Slot.bin`。

加密存档解密依赖本仓库自带的 MandarinJuice CLI 和 Onimusha profile。SteamID 用环境变量，不要写进仓库：

```bash
set ONIMUSHA_STEAM_ID=你的64位SteamID
```

也可以在 `scripts/steamid.txt` 放一行（该文件已被 git 忽略）。

## 仓库里有什么

- `web/`：阅览页（Vite + React）
- `scripts/analyze_bin.py`：解密并打成页面用的 JSON
- `scripts/parse_save.py`、`scripts/make_display_data.py`：明文解析
- `dumps/rszoniwots.json`、`dumps/oniwots_enums.json`：解析用的类型表
- `tools/mandarin_cli/`：存档解密 CLI

个人存档、SteamID、其它游戏的解密 profile 都没有提交。

## 说明

`GameOverCount` 不是每次倒下/检查点重试的次数，页面上不再显示“死亡”。通关次数来自栏位里的 `ClearCount`。
