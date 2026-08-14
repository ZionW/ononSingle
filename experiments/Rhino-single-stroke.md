# ononSingle Rhino Experimental

這是一個模仿 Rhino 內建 `MecSoft_Font-1` 與 `SLF-RHN Architect` 輪廓結構的辨識測試版，不會取代 `ononSingle.ttf`。

## 與 Text 相容實驗版的差別

- `ononSingleText-Experimental.ttf`：使用極細封閉輪廓，標準填色顯示正常，但炸開後是雙線。
- `ononSingleRhino-Experimental.ttf`：使用真正的單向退化輪廓，並加入 `Engraving: Singlestroke` 描述，測試 Rhino 能否將它視為單線雕刻字型。

## 為什麼仍需在 Rhino 實測

Rhino 官方文件指出軟體會維護一份已知雕刻字型清單。內建的 `MecSoft_Font-1` 與 `SLF-RHN Architect` 能在 `Text` 炸開後保持單線，可能不只依賴輪廓與 metadata，也可能依賴 Rhino 內部的家族名稱辨識。

本測試版保留自己的 `ononSingle Rhino Experimental` 家族名稱，不冒用兩個內建字型名稱。因此：

- 如果 Rhino 讀取 `Engraving: Singlestroke` metadata，這版應能在 `Text` 炸開後保持單線。
- 如果 Rhino 只接受內建白名單，仍會出現封口線或異常顯示；這種情況只能請 McNeel 將 `ononSingle` 加入已知雕刻字型清單，或由外掛處理炸開曲線。

## 測試方式

1. 安裝 `ononSingleRhino-Experimental.ttf` 並重新啟動 Rhino。
2. 使用一般 `Text` 建立 `RHINO 單線字測試 l I 一`。
3. 執行 `Explode`。
4. 確認每條筆畫是否只有一條曲線，以及端點之間是否出現額外封口線。

## 重建

```sh
python3 tools/build_rhino_single_stroke.py \
  ononSingle.ttf ononSingleRhino-Experimental.ttf
```
