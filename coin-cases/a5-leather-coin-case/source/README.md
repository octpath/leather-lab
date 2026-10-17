# A5 Leather Coin Case — Source

[geometry.json](geometry.json)を、PDFと3D型紙の輪郭・穴中心の共通データとして使います。
単位はmm、原点は各パーツ外接矩形の左上、xは右向き・yは下向きです。
CAD側でyを上向きへ変換し、平らな下面をz=0に置きます。

## ファイル

| ファイル | 用途 |
| --- | --- |
| [geometry.json](geometry.json) | 確定輪郭、縫い穴・丸錐・ホック中心、取付位置、A5配置 |
| [build_pattern.py](build_pattern.py) | 原寸PDF生成 |
| [build_templates.py](build_templates.py) | SCAD座標データと5種類のSTL生成 |
| [template-data.scad](template-data.scad) | OpenSCADで読み込む座標データ。JSONから再生成 |
| [reinforcement.json](reinforcement.json) | 3D専用の補強寸法、窓・桟の配置。寸法は試作値 |
| [reinforcement.py](reinforcement.py) | 共通の2D断面と、残り幅・骨格の接続・工具の逃げの検査 |
| [verify.py](verify.py) | 元座標と、PDFベクター・STL断面との照合 |
| [qa.json](qa.json) | 検証結果と検証対象ファイルのSHA-256 |
| [check_slices.py](check_slices.py) | PrusaSlicerの実際の押出経路を検査 |
| [slice-check.ini](slice-check.ini) | 経路検査専用の仮設定。P1S用の機械設定ではない |
| [slice-qa.json](slice-qa.json) | スライス検査結果とSTLのSHA-256 |
| [build_previews.py](build_previews.py) | PDFと3D型紙のプレビュー生成 |
| [requirements.txt](requirements.txt) | 再生成・検証に使うPython依存パッケージ |

## 再生成

Python 3.12とOpenSCAD CLIを使います。プロジェクトのルートから実行する例です。

```sh
python -m pip install -r source/requirements.txt
python source/build_templates.py --jobs 2
python source/verify.py
python source/check_slices.py --slicer prusa-slicer
python source/build_previews.py
```

PDFの再生成が必要な場合は、別途`python source/build_pattern.py`を実行します。3Dの補強寸法だけを変える際には不要です。

個別STLの生成は既定で2プロセス、`--jobs`は1〜4です。一括版は生成済みの4枚を同じ座標に配置して構成します。生成物は同名のファイルを更新します。
JSONから座標データだけ更新する場合は、`python source/build_templates.py --data-only`を使います。
個別STLを再利用して一括配置だけ作り直す場合は、`python source/build_templates.py --layout-only`を使います。
OpenSCAD原稿の板厚・穴径を変更した場合は、JSONの`printing`も合わせて更新して検証します。
補強寸法を変更するときは、`reinforcement.json`とOpenSCADの既定値を合わせます。生成前に両者の一致と最小残り幅を検査します。
パーツごとの窓は`[中心x, 中心y, 幅, 高さ]`、桟は両端の座標です。DはCの鏡像として展開します。
窓の寸法倍率と中心間隔倍率、枠幅、リブの幅・高さ・位置、根元、工具の逃げ、最小残り幅を別のパラメーターとして持ちます。

OpenSCADは、基準部・上部の溝・リブ根元・リブ上部を、それぞれ2D断面から押し出して接続します。
平板部は2mm、リブは追加1.4mm、全高3.4mmです。基準部のガイド穴径1.1mmとホック穴径2.1／3.6mmを保持し、リブ部分だけに広い工具の逃げを設けます。

## 座標と縫い方

- かぶせの45度角落としは縦横10.242640687mm、本体幅は74.970562748mmです。かぶせの縫い線は、先端52mm・斜辺各12mmを4mmピッチで割っています。
- かぶせ裏の高さは30.485281374mm、本体全高は169.485281374mmです。表の表示寸法だけを丸め、座標は丸めません。
- マチの縫い線は底辺64mm・斜辺36mm・立ち上がり34mmです。立ち上がりは自由端から2mmの丸錐位置を起点に4mm刻みです。
- A・C・Dの共通穴は同じ縫い線上の位置を参照します。取付境界の本体だけの丸錐穴は、部品間の逃げにあります。その前後の4.75／5mmを、4mmへ均等化していません。
- Aの任意7号穴とBの7号穴は、同一の中心位置を使います。Aの下端側12号穴は端から12mm、かぶせ側・Bの7号穴は先端から18mmです。
- C・Dは鏡像です。一括STLの配置も、PDFのA5裁断配置と対応します。

## PDFの表示

| 用途 | RGB | 線幅・表示 |
| --- | --- | --- |
| 裁断線 | 0.12, 0.12, 0.12 | 実線0.6pt |
| 縫いガイド・穴中心 | 0.64, 0.30, 0.06 | ガイド実線0.35pt、中心点は表示径0.4mm |
| 取付位置 | 0.20, 0.43, 0.57 | 一点鎖線0.5pt、配列4 2 1 2 |

点の表示径を、実際の革の穴径や菱目の刃幅として使いません。
日本語は`assets/NotoSansJP-Regular.ttf`を埋め込み、既存のoctロゴを使います。
フォントの既存ライセンスは[assets/OFL.txt](assets/OFL.txt)にあります。

## 検証

検証スクリプトは、元座標の左右対称・共通穴・ピッチ・A5配置、PDFの原寸・線種・色・点の表示径・フォント・注記位置を確認します。
STLは閉じたメッシュ、外接寸法、全高、連結成分数、工具穴と貫通窓の数に加え、平板部の3断面で穴の中心と径を照合します。
基準部、溝のある上部、リブ根元、リブ上部の実際の断面を共通データとも照合し、リブの骨格が一続きであること、下の板から外れていないことを確認します。
CADの円を多角形で表す近似とSTLの数値精度を考慮し、STL中心誤差0.002mm未満、径誤差0.005mm未満を検査条件としています。

`check_slices.py`は[検査専用設定](slice-check.ini)で個別4枚をスライスし、複数の層で工具穴の開口、元の細い穴際とリブの経路数、押出領域の接続を検査します。
線幅はG-codeの各区間に記録された値を用い、可変幅のギャップ充填も区別します。開口の半径誤差の許容は0.04mm、押出領域の数値的な接続判定には片側0.02mmの許容を使います。
G-codeは一時ディレクトリへ作り、配布・コミットしません。`--work-dir`を指定すれば検査用の一時出力先を明示できます。
スライサーの仮の材料・温度・線幅等は[3Dの説明](../3d/README.md)に記録しています。P1Sの機械設定や使用材料を検証したものではありません。

検証結果はデータ上の確認です。今回の3D型紙の実機印刷・実革試作の確認とは区別しています。
