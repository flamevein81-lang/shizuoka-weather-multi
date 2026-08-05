import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timezone, timedelta
import platform

# 設定: 静岡 (地点番号: 47656 / prec_no: 50)
PREC_NO   = 50
BLOCK_NO  = 47656
YEARS     = [2024, 2025, 2026]   # 取得対象年度
CSV_PATH  = 'shizuoka_weather.csv'
IMAGE_PATH = 'shizuoka_weather_plot.png'
LOG_PATH  = 'weather_update.log'

JST = timezone(timedelta(hours=9))

# 日本語フォント設定
if platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'MS Gothic'
else:
    plt.rcParams['font.family'] = ['Noto Sans CJK JP', 'Noto Sans CJK', 'DejaVu Sans']


def log(message):
    """コンソールとファイルの両方にログを出力する"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(full_message + '\n')


# ─── データ取得 ──────────────────────────────────────────────────

def get_normal_data():
    """気象庁のHPから平年値 (1991-2020) の5日ごとのデータを取得する"""
    url = (f"https://www.data.jma.go.jp/stats/etrn/view/nml_sfc_mb5d.php"
           f"?prec_no={PREC_NO}&block_no={BLOCK_NO}&year=&month=&day=&view=p1")
    log(f"平年値データ取得中: {url}")

    try:
        response = requests.get(url, timeout=30)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.find('table', class_='data2_s')
        if not table:
            log("エラー: 平年値テーブルが見つかりませんでした。")
            return {}

        rows = table.find_all('tr')
        normal_dict = {}
        current_month = 1

        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) < 5:
                continue

            first_cell = cols[0].text.strip()

            period_idx = -1
            for i, col in enumerate(cols):
                if '半旬' in col.text:
                    period_idx = i
                    break
            if period_idx == -1:
                continue

            if period_idx == 1:
                m_str = first_cell.replace('月', '')
                if m_str.isdigit():
                    current_month = int(m_str)

            period_str = cols[period_idx].text.strip()
            period = int(period_str.replace('第', '').replace('半旬', ''))
            key = f"{current_month}/{period}"

            data_start_idx = period_idx + 2

            def to_f(val):
                try:
                    v = val.strip().replace(')', '').replace(']', '').replace(' ]', '')
                    return float(v)
                except:
                    return 0.0

            normal_dict[key] = {
                '平年降水量':   to_f(cols[data_start_idx].text),
                '平年平均気温': to_f(cols[data_start_idx + 1].text),
            }

        if not normal_dict:
            log("警告: 平年値データの解析結果が空です。")
        else:
            log(f"平年値データ取得完了: {len(normal_dict)}件")
        return normal_dict

    except Exception as e:
        log(f"平年値取得エラー: {e}")
        return {}


def get_year_data(year):
    """指定年の5日ごとの気象データを取得する（過去年は全データ、当年は完了済みのみ）"""
    url = (f"https://www.data.jma.go.jp/stats/etrn/view/mb5daily_s1.php"
           f"?prec_no={PREC_NO}&block_no={BLOCK_NO}&year={year}&month=&day=&view=")
    log(f"{year}年データ取得中: {url}")

    now = datetime.now(JST)
    is_past_year = (year < now.year)

    try:
        response = requests.get(url, timeout=30)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.find('table', class_='data2_s')
        if not table:
            log(f"{year}年: テーブルが見つかりませんでした。")
            return []

        rows = table.find_all('tr')
        data_list = []
        current_month = 1

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 5:
                continue

            first_text = cols[0].text.strip()
            if '半旬' not in first_text:
                m_str = first_text.replace('月', '')
                if m_str.isdigit():
                    current_month = int(m_str)
                base = 1
            else:
                base = 0

            period_str = cols[base].text.strip()
            if '半旬' not in period_str:
                continue

            period = int(period_str.replace('第', '').replace('半旬', ''))

            def to_f(val, is_precip=False):
                v = val.strip().replace(')', '').replace(']', '')
                if v in ('--', ''):
                    return 0.0 if is_precip else None
                try:
                    return float(v)
                except:
                    return None

            t_avg = to_f(cols[base + 8].text)

            # ── 取得範囲の判定 ──────────────────────────────────────
            # 過去年: 年をまたいだ誤判定を防ぐため全データ取得
            # 当年: 完了済み半旬のみ取得
            if is_past_year:
                pass  # スキップなし（全半旬取得）
            else:
                last_complete_period = (now.day - 1) // 5  # 0=なし, 1〜6
                if current_month > now.month:
                    continue  # 未来月はスキップ
                if current_month == now.month and period > last_complete_period:
                    continue  # 当月の未確定半旬はスキップ

            if t_avg is None:
                continue  # 値がない行はスキップ

            data_list.append({
                'Label':           f"{current_month}/{period}",
                f'{year}降水量':   to_f(cols[base + 4].text, True),
                f'{year}平均気温': t_avg,
            })

        log(f"{year}年データ取得完了: {len(data_list)}件")
        return data_list

    except Exception as e:
        log(f"{year}年データ取得エラー: {e}")
        return []


# ─── CSV 更新 ────────────────────────────────────────────────────

def update_csv(data_by_year, normal_dict):
    """各年の実測値と平年値を統合してCSVを保存する"""
    # 全ラベル（1/1 〜 12/6）を平年値に基づいて生成
    all_labels = [f"{m}/{p}" for m in range(1, 13) for p in range(1, 7)
                  if f"{m}/{p}" in normal_dict]

    rows = []
    for label in all_labels:
        row = {'Label': label}

        # 平年値
        nd = normal_dict.get(label, {})
        row['平年平均気温'] = nd.get('平年平均気温', np.nan)
        row['平年降水量']   = nd.get('平年降水量',   np.nan)

        # 各年の実測値
        for year in YEARS:
            year_map = {d['Label']: d for d in data_by_year.get(year, [])}
            yd = year_map.get(label, {})
            row[f'{year}平均気温'] = yd.get(f'{year}平均気温', np.nan)
            row[f'{year}降水量']   = yd.get(f'{year}降水量',   np.nan)

        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    log(f"CSVを更新しました: {CSV_PATH}（{len(df)}行）")
    return df


# ─── グラフ作成 ──────────────────────────────────────────────────

YEAR_STYLES = {
    2024: {'color': 'steelblue',  'marker': 'o'},
    2025: {'color': 'darkorange', 'marker': 's'},
    2026: {'color': 'crimson',    'marker': '^'},
}

def create_plot(df):
    """平均気温（4系列）と降水量（4系列）の比較グラフを作成する"""
    x = np.arange(len(df))
    labels = df['Label'].tolist()

    fig, ax1 = plt.subplots(figsize=(18, 9))

    # ── 気温（左軸）──
    ax1.plot(x, df['平年平均気温'], color='gray', linestyle='--',
             linewidth=1.5, alpha=0.7, label='平年 平均気温 (1991-2020)')
    for year, style in YEAR_STYLES.items():
        col = f'{year}平均気温'
        if col in df.columns:
            ax1.plot(x, df[col], color=style['color'], linestyle='-',
                     marker=style['marker'], markersize=4, linewidth=2.5,
                     label=f'{year}年 平均気温')

    ax1.set_xlabel('時期 (月/半旬)', fontsize=11)
    ax1.set_ylabel('平均気温 (℃)', fontsize=11)
    ax1.set_ylim(-5, 35)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=45, fontsize=8)
    ax1.legend(loc='upper left', ncol=2, fontsize='small')
    ax1.grid(True, linestyle=':', alpha=0.5)

    # ── 降水量（右軸）──
    ax2 = ax1.twinx()
    n_series = 1 + len(YEARS)  # 平年 + 各年
    width = 0.75 / n_series
    offsets = np.linspace(-(n_series - 1) / 2 * width,
                          (n_series - 1) / 2 * width, n_series)

    bar_specs = [('平年降水量', 'gray', '平年 降水量', 0.25)] + [
        (f'{y}降水量', YEAR_STYLES[y]['color'], f'{y}年 降水量', 0.55)
        for y in YEARS
    ]

    for i, (col, color, blabel, alpha) in enumerate(bar_specs):
        if col in df.columns:
            vals = df[col].fillna(0).values
            ax2.bar(x + offsets[i], vals, width,
                    alpha=alpha, color=color, label=blabel)

    ax2.set_ylabel('降水量 (mm)', fontsize=11)
    all_precip_cols = [s[0] for s in bar_specs if s[0] in df.columns]
    p_max_vals = [df[c].max() for c in all_precip_cols]
    p_max = max((v for v in p_max_vals if not np.isnan(v)), default=100)
    ax2.set_ylim(0, p_max * 1.6 + 30)
    ax2.legend(loc='upper right', ncol=2, fontsize='small')

    plt.title('静岡市の気象推移比較: 2024・2025・2026年 実測 vs 平年値 (1991-2020)',
              fontsize=13, pad=12)

    # X軸ラベルの間引き
    for i, t in enumerate(ax1.get_xticklabels()):
        if i % 3 != 0:
            t.set_visible(False)

    plt.tight_layout()
    plt.savefig(IMAGE_PATH, dpi=120)
    log(f"グラフを保存しました: {IMAGE_PATH}")
    plt.close()


# ─── メイン ─────────────────────────────────────────────────────

if __name__ == '__main__':
    log('--- 自動更新処理開始 ---')

    # 1. 平年値取得
    normal_dict = get_normal_data()

    # 2. 各年の実測値取得
    data_by_year = {}
    for year in YEARS:
        data_by_year[year] = get_year_data(year)

    # 3. CSV 更新
    df = update_csv(data_by_year, normal_dict)

    # 4. グラフ作成
    create_plot(df)

    log('--- 自動更新処理完了 ---')
