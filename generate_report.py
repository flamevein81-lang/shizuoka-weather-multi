"""
generate_report.py
静岡市 気象データ 多年度比較 (2024・2025・2026 vs 平年値) レポート生成スクリプト
CSVを読み込み、Chart.jsを用いたインタラクティブなHTMLレポートを出力する。
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime

# ─── パス設定 ────────────────────────────────────────────────────
WORKDIR     = os.path.dirname(os.path.abspath(__file__))
CSV_PATH    = os.path.join(WORKDIR, 'shizuoka_weather.csv')
OUTPUT_HTML = os.path.join(WORKDIR, 'index.html')
LOG_PATH    = os.path.join(WORKDIR, 'weather_update.log')

YEARS       = [2024, 2025, 2026]
STATION     = '静岡市'

YEAR_COLORS = {
    2024: {'border': '#2196F3', 'bg': 'rgba(33,150,243,0.15)'},
    2025: {'border': '#FF9800', 'bg': 'rgba(255,152,0,0.15)'},
    2026: {'border': '#F44336', 'bg': 'rgba(244,67,54,0.15)'},
}
NORMAL_COLOR = {'border': '#9E9E9E', 'bg': 'rgba(158,158,158,0.1)'}

BAR_COLORS = {
    '平年':  'rgba(158,158,158,0.4)',
    2024:    'rgba(33,150,243,0.6)',
    2025:    'rgba(255,152,0,0.6)',
    2026:    'rgba(244,67,54,0.6)',
}

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def safe(v):
    """NaN/None を JS の null に変換"""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    return round(float(v), 1)

def build_html(df, updated_at):
    labels   = df['Label'].tolist()
    labels_j = json.dumps(labels, ensure_ascii=False)

    # 気温データセット
    temp_datasets = []
    temp_datasets.append({
        'label':       '平年 平均気温 (1991-2020)',
        'data':        [safe(v) for v in df['平年平均気温']],
        'borderColor': NORMAL_COLOR['border'],
        'backgroundColor': NORMAL_COLOR['bg'],
        'borderWidth': 1.5,
        'borderDash':  [6, 4],
        'pointRadius': 2,
        'tension':     0.3,
        'fill':        False,
        'order':       10,
    })
    for year in YEARS:
        col = f'{year}平均気温'
        c = YEAR_COLORS[year]
        temp_datasets.append({
            'label':           f'{year}年 平均気温',
            'data':            [safe(v) for v in df.get(col, [])],
            'borderColor':     c['border'],
            'backgroundColor': c['bg'],
            'borderWidth':     2.5,
            'pointRadius':     3,
            'tension':         0.3,
            'fill':            False,
            'order':           YEARS.index(year),
        })

    # 降水量データセット
    prec_datasets = []
    prec_datasets.append({
        'label':           '平年 降水量',
        'data':            [safe(v) for v in df['平年降水量']],
        'backgroundColor': BAR_COLORS['平年'],
        'borderColor':     'rgba(158,158,158,0.7)',
        'borderWidth':     1,
        'order':           10,
    })
    for year in YEARS:
        col = f'{year}降水量'
        prec_datasets.append({
            'label':           f'{year}年 降水量',
            'data':            [safe(v) for v in df.get(col, [])],
            'backgroundColor': BAR_COLORS[year],
            'borderColor':     YEAR_COLORS[year]['border'],
            'borderWidth':     1,
            'order':           YEARS.index(year),
        })

    temp_js  = json.dumps(temp_datasets,  ensure_ascii=False)
    prec_js  = json.dumps(prec_datasets,  ensure_ascii=False)

    # 最新データ情報
    latest_label = df.dropna(subset=[f'{YEARS[-1]}平均気温']).iloc[-1]['Label'] \
        if not df.dropna(subset=[f'{YEARS[-1]}平均気温']).empty else '―'

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{STATION} 気象データ多年度比較 (2024-2026)</title>
  <meta name="description" content="{STATION}の気象データを2024・2025・2026年と平年値で比較するインタラクティブグラフ。気象庁データを自動取得。">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <style>
    :root {{
      --bg:        #0f1117;
      --surface:   #1a1d2e;
      --surface2:  #242740;
      --border:    #2d3154;
      --text:      #e8eaf0;
      --text-dim:  #8b90a8;
      --accent:    #5c6bc0;
      --blue:      #2196F3;
      --orange:    #FF9800;
      --red:       #F44336;
      --gray:      #9E9E9E;
      --radius:    12px;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Noto Sans JP', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
    }}

    /* ── ヘッダー ── */
    header {{
      background: linear-gradient(135deg, #1a1d2e 0%, #242740 50%, #1a1d2e 100%);
      border-bottom: 1px solid var(--border);
      padding: 28px 32px 22px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      flex-wrap: wrap;
      gap: 12px;
    }}
    header h1 {{
      font-size: clamp(1.1rem, 2.5vw, 1.6rem);
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    header h1 span {{ color: #7986cb; }}
    .header-meta {{
      font-size: 0.78rem;
      color: var(--text-dim);
      text-align: right;
      line-height: 1.7;
    }}

    /* ── レジェンドバッジ ── */
    .legend-bar {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      padding: 14px 32px;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 7px;
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 0.78rem;
      font-weight: 500;
      background: var(--surface2);
      border: 1px solid var(--border);
    }}
    .badge-dot {{
      width: 10px; height: 10px; border-radius: 50%;
    }}
    .dot-normal  {{ background: var(--gray); }}
    .dot-2024    {{ background: var(--blue); }}
    .dot-2025    {{ background: var(--orange); }}
    .dot-2026    {{ background: var(--red); }}

    /* ── メインコンテンツ ── */
    main {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 28px 24px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }}

    /* ── チャートカード ── */
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 24px;
      position: relative;
    }}
    .card-title {{
      font-size: 0.85rem;
      font-weight: 500;
      color: var(--text-dim);
      text-transform: uppercase;
      letter-spacing: 0.1em;
      margin-bottom: 18px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .card-title::before {{
      content: '';
      display: block;
      width: 3px;
      height: 16px;
      border-radius: 2px;
      background: var(--accent);
    }}
    .chart-wrap {{
      position: relative;
      height: 340px;
    }}
    @media (max-width: 600px) {{
      .chart-wrap {{ height: 260px; }}
    }}

    /* ── データテーブル ── */
    .table-wrap {{
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8rem;
    }}
    thead th {{
      background: var(--surface2);
      color: var(--text-dim);
      padding: 10px 12px;
      text-align: center;
      font-weight: 500;
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
    }}
    tbody tr:nth-child(even) {{ background: rgba(255,255,255,0.02); }}
    tbody tr:hover {{ background: rgba(92,107,192,0.08); }}
    tbody td {{
      padding: 8px 12px;
      text-align: center;
      border-bottom: 1px solid rgba(255,255,255,0.04);
    }}
    td.label {{ font-weight: 500; color: var(--text-dim); }}
    td.normal {{ color: var(--gray); }}
    td.y2024  {{ color: var(--blue); }}
    td.y2025  {{ color: var(--orange); }}
    td.y2026  {{ color: var(--red); font-weight: 600; }}
    td.null   {{ color: rgba(255,255,255,0.15); }}

    /* ── フッター ── */
    footer {{
      text-align: center;
      padding: 20px;
      font-size: 0.72rem;
      color: var(--text-dim);
      border-top: 1px solid var(--border);
    }}
    footer a {{ color: #7986cb; text-decoration: none; }}
  </style>
</head>
<body>

<header>
  <h1>📊 {STATION} 気象データ <span>多年度比較</span></h1>
  <div class="header-meta">
    最新データ: {latest_label}（{YEARS[-1]}年）<br>
    更新: {updated_at} ／ データ: <a href="https://www.jma.go.jp/" style="color:#7986cb">気象庁</a>
  </div>
</header>

<div class="legend-bar">
  <span class="badge"><span class="badge-dot dot-normal"></span>平年値（1991-2020）</span>
  <span class="badge"><span class="badge-dot dot-2024"></span>2024年</span>
  <span class="badge"><span class="badge-dot dot-2025"></span>2025年</span>
  <span class="badge"><span class="badge-dot dot-2026"></span>2026年</span>
</div>

<main>

  <!-- 平均気温チャート -->
  <div class="card">
    <div class="card-title">🌡 平均気温の推移（℃）</div>
    <div class="chart-wrap">
      <canvas id="tempChart"></canvas>
    </div>
  </div>

  <!-- 降水量チャート -->
  <div class="card">
    <div class="card-title">🌧 降水量の推移（mm）</div>
    <div class="chart-wrap">
      <canvas id="precChart"></canvas>
    </div>
  </div>

  <!-- データテーブル -->
  <div class="card">
    <div class="card-title">📋 データ一覧</div>
    <div class="table-wrap">
      <table id="dataTable">
        <thead>
          <tr>
            <th>期間</th>
            <th>平年 気温</th>
            <th>2024年 気温</th>
            <th>2025年 気温</th>
            <th>2026年 気温</th>
            <th>平年 降水量</th>
            <th>2024年 降水量</th>
            <th>2025年 降水量</th>
            <th>2026年 降水量</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
    </div>
  </div>

</main>

<footer>
  データ出典: <a href="https://www.data.jma.go.jp/stats/etrn/" target="_blank">気象庁 過去の気象データ検索</a>
  ／ 気象観測地点: {STATION} (地点番号: 47656)
  ／ GitHub Actions による自動更新
</footer>

<script>
const LABELS = {labels_j};
const TEMP_DATASETS = {temp_js};
const PREC_DATASETS = {prec_js};

// ── 共通オプション ──
const gridColor = 'rgba(255,255,255,0.06)';
const tickColor = '#8b90a8';
const commonScales = (yLabel) => ({{
  x: {{
    ticks: {{ color: tickColor, maxRotation: 45, autoSkip: true, maxTicksLimit: 24 }},
    grid:  {{ color: gridColor }},
  }},
  y: {{
    ticks: {{ color: tickColor }},
    grid:  {{ color: gridColor }},
    title: {{ display: true, text: yLabel, color: tickColor, font: {{ size: 11 }} }},
  }},
}});

const tooltipPlugin = {{
  backgroundColor: 'rgba(26,29,46,0.95)',
  titleColor: '#e8eaf0',
  bodyColor: '#b0b5cc',
  borderColor: '#2d3154',
  borderWidth: 1,
  padding: 10,
}};

// ── 気温チャート ──
new Chart(document.getElementById('tempChart'), {{
  type: 'line',
  data: {{ labels: LABELS, datasets: TEMP_DATASETS }},
  options: {{
    responsive: true, maintainAspectRatio: false, animation: {{ duration: 600 }},
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{
      legend: {{ labels: {{ color: '#e8eaf0', font: {{ size: 11 }}, boxWidth: 20 }} }},
      tooltip: tooltipPlugin,
    }},
    scales: {{
      ...commonScales('平均気温 (℃)'),
      y: {{ ...commonScales('').y, suggestedMin: 0, suggestedMax: 32 }},
    }},
  }},
}});

// ── 降水量チャート ──
new Chart(document.getElementById('precChart'), {{
  type: 'bar',
  data: {{ labels: LABELS, datasets: PREC_DATASETS }},
  options: {{
    responsive: true, maintainAspectRatio: false, animation: {{ duration: 600 }},
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{
      legend: {{ labels: {{ color: '#e8eaf0', font: {{ size: 11 }}, boxWidth: 20 }} }},
      tooltip: tooltipPlugin,
    }},
    scales: {{
      ...commonScales('降水量 (mm)'),
      x: {{ ...commonScales('').x, stacked: false }},
      y: {{ ...commonScales('降水量 (mm)').y, min: 0 }},
    }},
  }},
}});

// ── テーブル生成 ──
const TEMP_VALS = TEMP_DATASETS.map(d => d.data);
const PREC_VALS = PREC_DATASETS.map(d => d.data);
const tbody = document.getElementById('tableBody');

const fmt = (v, cls) => v === null
  ? `<td class="null">―</td>`
  : `<td class="${{cls}}">${{v}}°</td>`;
const fmtP = (v, cls) => v === null
  ? `<td class="null">―</td>`
  : `<td class="${{cls}}">${{v}} mm</td>`;

LABELS.forEach((lbl, i) => {{
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td class="label">${{lbl}}</td>
    ${{fmt(TEMP_VALS[0][i], 'normal')}}
    ${{fmt(TEMP_VALS[1][i], 'y2024')}}
    ${{fmt(TEMP_VALS[2][i], 'y2025')}}
    ${{fmt(TEMP_VALS[3][i], 'y2026')}}
    ${{fmtP(PREC_VALS[0][i], 'normal')}}
    ${{fmtP(PREC_VALS[1][i], 'y2024')}}
    ${{fmtP(PREC_VALS[2][i], 'y2025')}}
    ${{fmtP(PREC_VALS[3][i], 'y2026')}}
  `;
  tbody.appendChild(tr);
}});
</script>
</body>
</html>
"""
    return html


def main():
    log('--- レポート生成開始 ---')

    if not os.path.exists(CSV_PATH):
        log(f"エラー: CSVファイルが見つかりません: {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    log(f"CSVを読み込みました: {len(df)}行")

    updated_at = datetime.now().strftime('%Y-%m-%d %H:%M JST')
    html = build_html(df, updated_at)

    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    log(f"レポートを出力しました: {OUTPUT_HTML}")
    log('--- レポート生成完了 ---')


if __name__ == '__main__':
    main()
