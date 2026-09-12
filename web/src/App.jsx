import { useEffect, useMemo, useRef, useState } from "react";
import collectibles from "./data/collectibles.json";
import { loadLatestSave, loadSteamId, saveLatestSave, saveSteamId } from "./saveStore";

function sameId(a, b) {
  if (a == null || b == null) return false;
  return (Number(a) >>> 0) === (Number(b) >>> 0);
}

function formatNum(value) {
  return Number(value || 0).toLocaleString("zh-CN");
}

function ratio(owned, total) {
  if (owned == null) return "未解析";
  return `${owned} / ${total}`;
}

function amuletName(item) {
  const names = collectibles.amuletNames || {};
  const catalog = collectibles.amulets || [];
  const byId = names[String(item.SeriesId)] || names[String(Number(item.SeriesId) >>> 0)];
  if (byId) return byId;
  const row = catalog.find(
    (it) => sameId(it.seriesId, item.SeriesId) || it.obtainUid === item.ObtainUid
  );
  return row?.name || `御守 ${item.ObtainUid || "?"}`;
}

function lanternLevelGroups(row) {
  return (row?.ids || []).map((item) => (Array.isArray(item) ? item : [item]));
}

function matchLantern(row, bags) {
  const levels = lanternLevelGroups(row);
  for (const bag of bags) {
    for (let i = 0; i < levels.length; i += 1) {
      if (levels[i].some((id) => sameId(id, bag?.MedicineBagID))) {
        return { bag, level: Math.min(i + 1, 3) };
      }
    }
  }
  return { bag: null, level: 1 };
}

function formatLevel(level, max = 3) {
  const n = level || 1;
  if (n >= max) return `${n} / ${max} 级 · 满`;
  return `${n} / ${max} 级`;
}

function formatGearLevel(piece) {
  const max = piece?.maxLevel || 5;
  const level = Math.min(piece?.level || 1, max);
  if (piece?.maxed) return `${level} / ${max} 级 · 满`;
  return `${level} / ${max} 级`;
}

function formatGearSmall(piece) {
  if (!piece || piece.maxed || !piece.smallTotal) return null;
  return `小等级 ${piece.smallOwned || 0} / ${piece.smallTotal}`;
}

function mysteryLabel(row, i) {
  if (row == null) return `幻魔杂记 ${i + 1}`;
  if (typeof row === "string") return row;
  return row.name || `幻魔杂记 ${i + 1}`;
}

function mysteryOwned(row, i, bits, itemIds) {
  if (row?.itemId != null && itemIds.has(Number(row.itemId) >>> 0)) return true;
  if (row?.index != null) return bits.has(row.index);
  return bits.has(i);
}

function komainuGroups(bits, maps) {
  const owned = new Set(bits);
  let offset = 0;
  return (maps || []).map((area) => {
    const count = Number(area.count) || 0;
    const indexes = Array.from({ length: count }, (_, i) => offset + i);
    offset += count;
    return {
      ...area,
      indexes,
      owned: indexes.filter((bit) => owned.has(bit)).length,
    };
  });
}

function ownedAmulet(row, amulets) {
  return amulets.find(
    (it) =>
      sameId(it.SeriesId, row.seriesId) || Number(it.ObtainUid) === Number(row.obtainUid)
  );
}

function GearStat({ label, piece }) {
  const small = formatGearSmall(piece);
  return (
    <article className={`stat${piece?.maxed ? " maxed" : ""}`}>
      <span>{label}</span>
      <b>{formatGearLevel(piece)}</b>
      {small ? <em>{small}</em> : null}
    </article>
  );
}

const COLLECTION_TABS = [
  { id: "weapons", label: "鬼之武具" },
  { id: "lanterns", label: "鬼灯袋" },
  { id: "amulets", label: "御守" },
  { id: "komainu", label: "狛犬" },
  { id: "mysteries", label: "幻魔杂记" },
  { id: "bosses", label: "Boss" },
  { id: "achievements", label: "Steam 成就" },
];

const ACHIEVEMENT_GROUPS = [
  { id: "boss", label: "故事 Boss" },
  { id: "rematch", label: "再战" },
  { id: "collect", label: "收集" },
  { id: "combat", label: "战斗" },
  { id: "story", label: "通关" },
  { id: "meta", label: "总成就" },
];

function achievementProgress(item) {
  if (item?.target) return `${item.count || 0} / ${item.target}`;
  if (item?.count) return `${item.count}`;
  return null;
}

function bossLabel(item) {
  if (!item?.boss) return item?.name || "Boss";
  return item.place ? `${item.boss}（${item.place}）` : item.boss;
}

function formatUploadedAt(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function normalizeSteamId(value) {
  return String(value || "").replace(/\s+/g, "").trim();
}

function BrandMark() {
  return <img className="brand-name" src="/image/name.webp" alt="鬼武者：剑之道" />;
}

function SteamIdField({ id, value, onChange, disabled }) {
  return (
    <label className="steam-field" htmlFor={id}>
      <span>SteamID64</span>
      <input
        id={id}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        spellCheck={false}
        placeholder="Steam个人资料页面链接最后那串数字，一般以7656119开头"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(normalizeSteamId(event.target.value))}
      />
    </label>
  );
}

function FilePicker({ id, onFile, disabled, children, className }) {
  const inputRef = useRef(null);
  return (
    <>
      <input
        id={id}
        ref={inputRef}
        className="file-input"
        type="file"
        accept=".bin,application/octet-stream"
        disabled={disabled}
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file) onFile(file);
        }}
      />
      <button
        type="button"
        className={className}
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        {children}
      </button>
    </>
  );
}

function UploadGate({ onFile, busy, error, dragging, setDragging, steamId, onSteamIdChange }) {
  return (
    <div className="page upload-page">
      <div className="mist" />
      <div className="page-sheet">
      <header className="hero">
      <BrandMark />
        <h1 className="page-title">存档阅览</h1>
        <p className="hero-note">仅支持Steam存档，解密需要.bin后缀存档和SteamID</p>
        <p className="hero-note">存档和SteamID只存在于浏览器本地存储，不会被上传到服务器</p>
      </header>
      <SteamIdField id="steam-id" value={steamId} onChange={onSteamIdChange} disabled={busy} />
      <label
        className={`drop-zone${dragging ? " dragging" : ""}${busy ? " busy" : ""}`}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setDragging(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          const file = event.dataTransfer.files?.[0];
          if (file) onFile(file);
        }}
      >
        <input
          className="file-input"
          type="file"
          accept=".bin,application/octet-stream"
          disabled={busy}
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (file) onFile(file);
          }}
        />
        <strong>{busy ? "正在解析存档…" : "把存档拖到这里，或点这里选择文件"}</strong>
        <span>只接受.bin后缀存档。解析在本机完成，SteamID与存档只存在于浏览器本地存储，不会被上传到服务器</span>
      </label>
      <p>存档位置一般在：</p>
      <p>C:\Users\你的用户名\steam\userdata\一串数字\2638890\remote\win64_save</p>
      <p>存档文件一般是 data001Slot.bin</p>
      {error ? <p className="upload-error">{error}</p> : null}
      </div>
      {busy ? (
        <div className="busy-mask">
          <p>正在解密并解析存档…</p>
        </div>
      ) : null}
    </div>
  );
}

export default function App() {
  const [record, setRecord] = useState(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [steamId, setSteamId] = useState("");

  useEffect(() => {
    setSteamId(loadSteamId());
    loadLatestSave()
      .then((saved) => {
        if (saved?.save) setRecord(saved);
      })
      .catch(() => {})
      .finally(() => setReady(true));
  }, []);

  function handleSteamIdChange(value) {
    setSteamId(value);
    saveSteamId(value);
  }

  async function submitFile(file) {
    if (!file) return;
    const name = file.name || "data001Slot.bin";
    if (!name.toLowerCase().endsWith(".bin")) {
      setError("请提交 .bin 存档文件");
      return;
    }
    const sid = normalizeSteamId(steamId);
    if (!sid) {
      setError("请填写 SteamID");
      return;
    }
    if (!/^\d{6,20}$/.test(sid)) {
      setError("SteamID 应为 6～20 位数字");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const body = await file.arrayBuffer();
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/octet-stream",
          "X-Filename": encodeURIComponent(name),
          "X-Steam-Id": sid,
        },
        body,
      });
      const payload = await response.json();
      if (!response.ok || payload.error) {
        throw new Error(payload.error || "解析失败");
      }
      const next = {
        save: payload.save,
        filename: payload.filename || name,
        uploadedAt: payload.uploadedAt || new Date().toISOString(),
      };
      setRecord(next);
      try {
        await saveLatestSave(next);
      } catch {
        setError("分析结果已显示，但浏览器没能记住这次提交");
      }
    } catch (err) {
      setError(err.message || "解析失败");
    } finally {
      setBusy(false);
    }
  }

  if (!ready) {
    return (
      <div className="page upload-page">
        <div className="mist" />
        <div className="page-sheet">
          <BrandMark />
          <p className="hero-note">正在读取本地记录…</p>
        </div>
      </div>
    );
  }

  if (!record?.save) {
    return (
      <UploadGate
        onFile={submitFile}
        busy={busy}
        error={error}
        dragging={dragging}
        setDragging={setDragging}
        steamId={steamId}
        onSteamIdChange={handleSteamIdChange}
      />
    );
  }

  return (
    <SaveViewer
      saveFile={record.save}
      filename={record.filename}
      uploadedAt={record.uploadedAt}
      onFile={submitFile}
      busy={busy}
      error={error}
      steamId={steamId}
      onSteamIdChange={handleSteamIdChange}
    />
  );
}

function SaveViewer({ saveFile, filename, uploadedAt, onFile, busy, error, steamId, onSteamIdChange }) {
  const slots = saveFile.slots || [saveFile];
  const [selected, setSelected] = useState(0);
  const [collectionTab, setCollectionTab] = useState(null);

  useEffect(() => {
    setSelected(0);
    setCollectionTab(null);
  }, [saveFile]);
  const save = slots[Math.min(selected, Math.max(slots.length - 1, 0))] || saveFile;
  const amulets = save.amulets || [];
  const bags = save.medicineBags || [];
  const collections = save.collections || {};
  const usedCount = slots.length;
  const capacity = saveFile.totalSlotCapacity || 21;
  const weaponCatalog = collectibles.oniWeapons || [];
  const mysteryCatalog = collectibles.mysteries || [];
  const unlockedWeapons = collections.oniWeapons?.unlockedIds || [];
  const mysteryBits = new Set(collections.mysteries?.bits || []);
  const mysteryItemIds = new Set(
    (collections.mysteries?.itemIds || []).map((id) => Number(id) >>> 0)
  );
  const komainuMaps = collectibles.komainuMaps || collections.komainu?.maps || [];
  const komainuGroupsRows = komainuGroups(collections.komainu?.bits || [], komainuMaps);
  const amuletTarget = collections.amulets?.total || 15;
  const lanternTotal = collectibles.totals?.lanterns || collections.lanterns?.total || 5;
  const lanternCatalog = collectibles.lanterns || [];
  const lanternRows = lanternCatalog.map((row) => {
    const matched = matchLantern(row, bags);
    return { row, ...matched, owned: Boolean(matched.bag) };
  });
  const lanternOwned = lanternRows.filter((it) => it.owned).length;
  const lanternLevel3 = lanternRows.filter((it) => it.owned && it.level >= 3).length;
  const amuletCatalog = collectibles.amulets || [];
  const equipment = save.equipment || {};
  const extraAmulets = amulets.filter(
    (item) =>
      !amuletCatalog.some(
        (row) =>
          sameId(item.SeriesId, row.seriesId) || Number(item.ObtainUid) === Number(row.obtainUid)
      )
  );
  const achievements = saveFile.achievements || {};
  const achievementItems = achievements.items || [];
  const bosses = saveFile.bosses || achievements.bosses || {};
  const bossItems = bosses.items || [];

  const slotLabel = useMemo(() => {
    if (save.isAutosave) return `自动存档 ${save.slotIndex}`;
    return `栏位 ${save.slotIndex}`;
  }, [save.isAutosave, save.slotIndex]);

  return (
    <div className="page viewer-page">
      <div className="mist" />
      <div className="page-sheet">
      <header className="hero">
      <BrandMark />
        <div className="hero-row">
          <div>
            <h1 className="page-title">存档阅览</h1>
            <p className="slot">
              {slotLabel}
              {save.location ? ` · ${save.location}` : ""}
            </p>
            <p className="hero-note">
              当前文件 {filename || "data001Slot.bin"}
              {uploadedAt ? ` · ${formatUploadedAt(uploadedAt)} 提交` : ""}
            </p>
          </div>
          <div className="hero-actions">
            <SteamIdField
              id="steam-id-viewer"
              value={steamId}
              onChange={onSteamIdChange}
              disabled={busy}
            />
            <FilePicker className="replace-btn" onFile={onFile} disabled={busy}>
              {busy ? "正在解析…" : "更换存档"}
            </FilePicker>
          </div>
        </div>
        {error ? <p className="upload-error">{error}</p> : null}
      </header>

      <section className="slot-list">
        {slots.map((slot, i) => (
          <button
            key={`${slot.slotIndex}-${i}`}
            type="button"
            className={i === selected ? "slot-btn active" : "slot-btn"}
            onClick={() => setSelected(i)}
          >
            <span>{slot.isAutosave ? "自动" : `#${slot.slotIndex}`}</span>
            <strong>{slot.location || "（无地点）"}</strong>
            <em>游玩时长：{slot.playTime}</em>
          </button>
        ))}
      </section>

      <section className="mission">
        <div>
          <span className="label">当前目标</span>
          <strong>{save.objective || "—"}</strong>
        </div>
        <div className="mission-meta">
          <span>{formatNum(save.soulAmount)} 红魂</span>
          <span>{save.difficulty}</span>
          <span>{save.savedAt}</span>
        </div>
      </section>

      <section className="stats">
        <GearStat label="装束" piece={equipment.armor} />
        <GearStat label="刀" piece={equipment.sword} />
        <GearStat label="笼手" piece={equipment.gauntlet} />
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>收集度</h2>
          <p>点一项查看明细，再点一次收起</p>
        </div>
        <div className="collect-summary">
          {COLLECTION_TABS.map((tab) => {
            const extra =
              tab.id === "lanterns"
                ? lanternOwned
                  ? `${lanternLevel3} 个满级`
                  : "各 3 级"
                : tab.id === "amulets"
                  ? collections.amulets?.owned > amuletTarget
                    ? `${collections.amulets?.level3 || 0}个满级 有${collections.amulets.owned - amuletTarget}个额外御守`
                    : `${collections.amulets?.level3 || 0}个满级`
                  : tab.id === "komainu"
                    ? "6 张地图"
                    : tab.id === "bosses"
                      ? "全存档"
                      : tab.id === "achievements"
                        ? "全存档"
                        : "\u00a0";
            const value =
              tab.id === "weapons"
                ? ratio(collections.oniWeapons?.owned, collections.oniWeapons?.total || 6)
                : tab.id === "lanterns"
                  ? ratio(lanternOwned, lanternTotal)
                  : tab.id === "amulets"
                    ? ratio(collections.amulets?.owned, amuletTarget)
                    : tab.id === "komainu"
                      ? ratio(collections.komainu?.owned, collections.komainu?.total || 36)
                      : tab.id === "bosses"
                        ? ratio(bosses.owned, bosses.total || 15)
                        : tab.id === "achievements"
                          ? ratio(achievements.owned, achievements.total || 52)
                          : ratio(collections.mysteries?.owned, collections.mysteries?.total || 23);
            const active = collectionTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                className={active ? "collect-btn active" : "collect-btn"}
                aria-pressed={active}
                onClick={() => setCollectionTab(active ? null : tab.id)}
              >
                <span>{tab.label}</span>
                <b>{value}</b>
                <em>{extra}</em>
              </button>
            );
          })}
        </div>

        {collectionTab === "weapons" ? (
          <div className="collect-detail">
            <div className="panel-head">
              <h2>鬼之武具</h2>
              {/* <p>{collectibles.notes?.oniWeapons}</p> */}
            </div>
            <div className="weapon-grid">
              {weaponCatalog.map((weapon) => {
                const owned = unlockedWeapons.some((id) => sameId(id, weapon.id));
                return (
                  <div className={`weapon-card${owned ? " owned" : ""}`} key={weapon.id}>
                    <span>{owned ? "已收集" : "未收集"}</span>
                    <strong>{weapon.name}</strong>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}

        {collectionTab === "lanterns" ? (
          <div className="collect-detail">
            <div className="panel-head">
              <h2>鬼灯袋</h2>
              {/* <p>{collectibles.notes?.lanterns}</p> */}
            </div>
            <div className="weapon-grid">
              {lanternRows.map(({ row, owned, level }) => (
                <div
                  className={`weapon-card${owned ? " owned" : ""}${owned && level >= 3 ? " maxed" : ""}`}
                  key={`bag-${row.index}`}
                >
                  <span>{owned ? (level >= 3 ? "满级" : "已收集") : "未收集"}</span>
                  <strong>{row.name}</strong>
                  <em>{owned ? formatLevel(level) : null}</em>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {collectionTab === "amulets" ? (
          <div className="collect-detail">
            <div className="panel-head">
              <h2>御守</h2>
              {/* <p>{collectibles.notes?.amulets}</p> */}
            </div>
            <div className="weapon-grid amulet-grid">
              {amuletCatalog.map((row) => {
                const item = ownedAmulet(row, amulets);
                const owned = Boolean(item);
                const maxed = owned && (item.level || 1) >= 3;
                return (
                  <div
                    className={`weapon-card${owned ? " owned" : ""}${maxed ? " maxed" : ""}`}
                    key={`amulet-${row.obtainUid}-${row.seriesId}`}
                  >
                    <span>{owned ? (maxed ? "满级" : "已收集") : "未收集"}</span>
                    <strong>{owned ? amuletName(item) : row.name}</strong>
                    <em>{owned ? formatLevel(item.level) : null}</em>
                  </div>
                );
              })}
              {extraAmulets.map((item) => {
                const maxed = (item.level || 1) >= 3;
                return (
                  <div className={`weapon-card owned${maxed ? " maxed" : ""}`} key={`amulet-extra-${item.ObtainUid}-${item.SeriesId}`}>
                    <span>{maxed ? "满级" : "已收集"}</span>
                    <strong>{amuletName(item)}</strong>
                    <em>{formatLevel(item.level)}</em>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}

        {collectionTab === "komainu" ? (
          <div className="collect-detail">
            <div className="panel-head">
              <h2>狛犬</h2>
            </div>
            {komainuGroupsRows.map((area) => (
              <div className="collect-map" key={`komainu-map-${area.index}`}>
                <div className="collect-map-head">
                  <strong>{area.name}</strong>
                  <span>{area.count ? `${area.owned} / ${area.count}` : "无"}</span>
                </div>
                {area.count ? (
                  <div className="weapon-grid mystery-grid">
                    {area.indexes.map((bit, i) => {
                      const owned = (collections.komainu?.bits || []).includes(bit);
                      return (
                        <div className={`weapon-card${owned ? " owned" : ""}`} key={`komainu-${bit}`}>
                          <span>{owned ? "已救助" : "未救助"}</span>
                          <strong>{`${area.name} ${i + 1}`}</strong>
                        </div>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}

        {collectionTab === "mysteries" ? (
          <div className="collect-detail">
            <div className="panel-head">
              <h2>幻魔杂记</h2>
            </div>
            <div className="weapon-grid mystery-grid">
              {Array.from({ length: mysteryCatalog.length || collections.mysteries?.total || 23 }, (_, i) => {
                const owned = mysteryOwned(mysteryCatalog[i], i, mysteryBits, mysteryItemIds);
                return (
                  <div className={`weapon-card${owned ? " owned" : ""}`} key={`mystery-${i}`}>
                    <span>{owned ? "已收集" : "未收集"}</span>
                    <strong>{mysteryLabel(mysteryCatalog[i], i)}</strong>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}

        {collectionTab === "bosses" ? (
          <div className="collect-detail">
            <div className="panel-head">
              <h2>Boss</h2>
              <p>全存档共享</p>
            </div>
            <div className="weapon-grid mystery-grid">
              {bossItems.map((item) => (
                <div className={`weapon-card${item.unlocked ? " owned" : ""}`} key={`boss-${item.enumId}`}>
                  <span>{item.unlocked ? "已击败" : "未击败"}</span>
                  <strong>{bossLabel(item)}</strong>
                  <em>{item.desc}</em>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {collectionTab === "achievements" ? (
          <div className="collect-detail">
            <div className="panel-head">
              <h2>Steam 成就</h2>
              <p>全存档共享</p>
            </div>
            {ACHIEVEMENT_GROUPS.map((group) => {
              const rows = achievementItems.filter((item) => item.group === group.id);
              if (!rows.length) return null;
              const owned = rows.filter((item) => item.unlocked).length;
              return (
                <div className="collect-map" key={`ach-group-${group.id}`}>
                  <div className="collect-map-head">
                    <strong>{group.label}</strong>
                    <span>{`${owned} / ${rows.length}`}</span>
                  </div>
                  <div className="weapon-grid mystery-grid">
                    {rows.map((item) => {
                      const progress = achievementProgress(item);
                      return (
                        <div className={`weapon-card${item.unlocked ? " owned" : ""}`} key={`ach-${item.enumId}`}>
                          <span>{item.unlocked ? "已解锁" : "未解锁"}</span>
                          <strong>{item.name}</strong>
                          <em>{progress ? `${item.desc} · ${progress}` : item.desc}</em>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        ) : null}
      </section>

      <footer>
        解析只在本机进行，最后一次提交的结果会记在这个浏览器里，不会传到网上
      </footer>
      </div>
      {busy ? (
        <div className="busy-mask">
          <p>正在解密并解析存档…</p>
        </div>
      ) : null}
    </div>
  );
}
