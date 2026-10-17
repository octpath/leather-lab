# A5 Leather Coin Case — 3D Templates

裁断のケガキと、菱目打ち・丸錐・ホックの位置写しに使う平板型紙です。
底面はz=0の平面です。単位はmm、外形と穴中心は[PDF](../pdf/a5-leather-coin-case-pattern.pdf)と共通です。
通常は、以下の個別STLを1パーツずつ使います。

## ファイル

| ファイル | パーツ |
| --- | --- |
| [a-body-template.stl](a-body-template.stl) | A・本体 |
| [b-flap-liner-template.stl](b-flap-liner-template.stl) | B・かぶせ裏 |
| [c-left-gusset-template.stl](c-left-gusset-template.stl) | C・左マチ |
| [d-right-gusset-template.stl](d-right-gusset-template.stl) | D・右マチ |
| [a5-leather-coin-case-templates.scad](a5-leather-coin-case-templates.scad) | 編集・再出力用OpenSCAD |

必要な個別STLをスライサーへ読み込み、底面を下にして配置・印刷します。
参考用の[一括配置STL](a5-leather-coin-case-templates.stl)は、4個の独立した板を並べたものです。外接寸法は約113.97×201.97×2mmです。

## 既定値

| 設定 | 値 |
| --- | --- |
| プリンター・ノズル | Bambu Lab P1S・0.4mm |
| `plate_t` | 2mm |
| `guide_d` | 1.1mm・丸い貫通穴 |
| `snap7_d` | 2.1mm |
| `snap12_d` | 3.6mm |
| `include_optional_flap_snap` | `true` |
| `engrave_attachment_lines` | `true` |
| `attachment_width` / `attachment_depth` | 0.6mm / 0.3mm |

- 菱目打ち・丸錐の位置写しには、どちらも1.1mmの丸穴を使います。革への本穴の大きさを示す値ではありません。
- Aの下端側は12号3.6mm、Aのかぶせ側とBは7号2.1mmです。Aのかぶせ側は位置を用意しているだけで、革への穴あけは任意です。
- Aの上面の浅い溝が、PDFの青い取付位置線です。縫い位置の丸穴と交わらないよう、穴列を避けて中央と外縁に表示しています。
- 溝は上面だけにあり、革に当てる下面は平らです。上面の溝に合わせて外縁に目印を付け、型紙を外して線を結べます。
- 平板・貫通穴・上向きに開いた溝の形状なので、サポートを付けずに使う向きへ配置しています。材料と積層条件は使用する材料のP1Sプロファイルに合わせます。

## 使い方

1. 冷えた型紙の平面と穴の貫通を確認し、下面を革に当てます。
2. 外周をケガき、丸穴から縫い穴中心を軽く写します。Aの取付位置も写します。
3. 型紙を外し、革を裁断してから菱目打ち・丸錐で本穴をあけます。
4. ホック穴も、位置を写した後に型紙を外して7号または12号であけます。

## OpenSCAD

`part`を`A` / `B` / `C` / `D` / `layout`から選び、F6でレンダーしてSTLへ出力します。
初期表示は`A`です。`layout`は参考用の一括配置です。Aのかぶせ側の穴を型紙にも設けない場合は、`include_optional_flap_snap=false`にします。

板厚・ガイド穴径はパラメーターで変更できます。裁断輪郭と穴中心の編集は[geometry.json](../source/geometry.json)で行い、[再生成手順](../source/README.md)に従います。

データ上の寸法・穴・閉じた形状の検証は済んでいます。この4枚の実機印刷・実革への使用は未確認です。

[作品の説明へ](../README.md)
