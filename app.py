import streamlit as st
import requests
from bs4 import BeautifulSoup
from collections import Counter, defaultdict
import random
import itertools
import time

# --- 页面 UI 配置 ---
st.set_page_config(page_title="智彩 MAX PRO", page_icon="💰", layout="centered")

st.markdown("<h2 style='text-align: center; color: #07C160;'>💰 智彩 MAX PRO</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #7B7B7B;'>AI 多维算力引擎 · 云端永久版</p>", unsafe_allow_html=True)

# --- 侧边栏/控制面板 ---
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        lotto_type = st.selectbox("🎯 选择彩种", ["双色球", "大乐透", "福彩3D", "排列3"])
    with col2:
        limit = st.selectbox("📈 抓取期数", ["300", "500", "1000", "2000"], index=1)
        
    algo_type = st.selectbox(
        "🧠 核心推算模型",
        ["🏆聚合共识(全模型)", "🌟多维加权", "🧬遗传算法", "🎲蒙特卡洛", "🔗关联规则", "🔄马尔可夫"]
    )

# --- 核心网络与算法逻辑 ---
def fetch_and_calc(lotto_type, limit, algo_type):
    url_map = {
        "双色球": f"https://datachart.500.com/ssq/history/newinc/history.php?limit={limit}&sort=0",
        "大乐透": f"https://datachart.500.com/dlt/history/newinc/history.php?limit={limit}&sort=0",
        "福彩3D": f"https://datachart.500.com/sd/history/inc/history.php?limit={limit}&sort=0",
        "排列3": f"https://datachart.500.com/pls/history/inc/history.php?limit={limit}&sort=0"
    }
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    res = requests.get(url_map[lotto_type], headers=headers, timeout=15)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    history_data = []

    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) < 4: continue
        issue = tds[0].text.strip()
        if not issue.isdigit() or len(issue) < 5: continue
        try:
            if lotto_type == "双色球":
                reds = [td.text.strip() for td in tds[1:7]]
                blues = [tds[7].text.strip()]
            elif lotto_type == "大乐透":
                reds = [td.text.strip() for td in tds[1:6]]
                blues = [td.text.strip() for td in tds[6:8]]
            elif lotto_type in ["福彩3D", "排列3"]:
                raw_nums = tds[1].text.strip()
                if len(raw_nums.replace(" ", "")) >= 3:
                    nums = raw_nums.replace(" ", "")
                    reds = [nums[0], nums[1], nums[2]]
                else:
                    reds = [tds[1].text.strip(), tds[2].text.strip(), tds[3].text.strip()]
                blues = []
            if all(r.isdigit() for r in reds):
                history_data.append({"issue": issue, "reds": reds, "blues": blues})
        except: continue

    if len(history_data) < 50: return "❌ 拉取数据量不足，无法建立模型。"

    latest = history_data[0]
    l_reds_str = ' '.join(latest['reds'])
    l_blues_str = ' '.join(latest['blues'])
    out = f"✅ 数据拉取完毕 (共 {len(history_data)} 期)\n第 {latest['issue']} 期基准: [{l_reds_str} | {l_blues_str}]\n" + "-"*35 + "\n\n"

    is_big = lotto_type in ["双色球", "大乐透"]
    
    if is_big:
        red_dom = [str(x).zfill(2) for x in (range(1, 34) if lotto_type == "双色球" else range(1, 36))]
        blue_dom = [str(x).zfill(2) for x in (range(1, 17) if lotto_type == "双色球" else range(1, 13))]
        r_pick = 6 if lotto_type == "双色球" else 5
        b_pick = 1 if lotto_type == "双色球" else 2
    else:
        red_dom = [str(x) for x in range(10)]
        r_pick = 3
        blue_dom, b_pick = [], 0

    def run_multi():
        def calc(dom, h_list, l_nums):
            sc = {n: 0.0 for n in dom}
            for num in sc.keys():
                miss = 0
                for draw in h_list:
                    if num in draw: break
                    miss += 1
                if 2 <= miss <= 8: sc[num] += 3.0
                elif miss > 15: sc[num] += 1.5
                elif miss == 0: sc[num] += 0.5
            for draw in h_list:
                inter = set(draw).intersection(set(l_nums))
                if inter:
                    for num in draw:
                        if num not in l_nums: sc[num] += 0.5 * len(inter)
            for i in range(len(h_list)-1):
                if set(h_list[i+1]).intersection(set(l_nums)):
                    for num in h_list[i]: sc[num] += 2.0
            return [x[0] for x in sorted(sc.items(), key=lambda x: x[1], reverse=True)]
        
        if is_big:
            r_r = calc(red_dom, [d['reds'] for d in history_data], latest['reds'])
            b_r = calc(blue_dom, [d['blues'] for d in history_data], latest['blues'])
            return r_r[:r_pick], b_r[:b_pick]
        else:
            p1 = calc(red_dom, [[d['reds'][0]] for d in history_data], [latest['reds'][0]])[0]
            p2 = calc(red_dom, [[d['reds'][1]] for d in history_data], [latest['reds'][1]])[0]
            p3 = calc(red_dom, [[d['reds'][2]] for d in history_data], [latest['reds'][2]])[0]
            return p1, p2, p3

    def run_ga():
        rc = Counter([r for d in history_data for r in d['reds']])
        bc = Counter([b for d in history_data for b in d['blues']])
        def solve(dom, pk, fc):
            pop = [random.sample(dom, pk) for _ in range(30)]
            for _ in range(20):
                pop = sorted(pop, key=lambda ch: sum([fc[g] for g in ch]), reverse=True)[:10]
                new_p = []
                while len(new_p) < 20:
                    p1, p2 = random.sample(pop, 2)
                    c = list(set(p1[:pk//2] + p2[pk//2:]))
                    while len(c)<pk: c.append(random.choice(dom)); c=list(set(c))
                    if random.random()<0.2: c[0]=random.choice(dom); c=list(set(c))
                    while len(c)<pk: c.append(random.choice(dom)); c=list(set(c))
                    new_p.append(c)
                pop.extend(new_p)
            return sorted(pop[0])
        if is_big: return solve(red_dom, r_pick, rc), solve(blue_dom, b_pick, bc)
        else: return str(random.randint(0,9)), str(random.randint(0,9)), str(random.randint(0,9))

    def run_mc():
        if is_big:
            ts = 102 if lotto_type == "双色球" else 90
            br, bd = [], 999
            for _ in range(2000):
                sim = random.sample(red_dom, r_pick)
                oc = sum(1 for x in sim if int(x)%2!=0)
                if oc==0 or oc==r_pick: continue
                df = abs(sum(int(x) for x in sim) - ts)
                if df < bd: bd, br = df, sim
            bc = Counter([b for d in history_data for b in d['blues']])
            return sorted(br), [x[0] for x in bc.most_common(b_pick)]
        else:
            return str(random.randint(0,9)), str(random.randint(0,9)), str(random.randint(0,9))

    def run_apriori():
        if is_big:
            prs = Counter()
            for d in history_data:
                for p in itertools.combinations(d['reds'], 2): prs[tuple(sorted(p))] += 1
            bp = prs.most_common(1)[0][0]
            fr = Counter()
            for d in history_data:
                if bp[0] in d['reds'] and bp[1] in d['reds']:
                    for r in d['reds']:
                        if r not in bp: fr[r] += 1
            tr = [x[0] for x in fr.most_common(r_pick - 2)]
            bc = Counter([b for d in history_data for b in d['blues']])
            return sorted(list(bp) + tr), [x[0] for x in bc.most_common(b_pick)]
        else: return run_multi()

    def run_markov():
        if is_big:
            rt, bt = defaultdict(Counter), defaultdict(Counter)
            for i in range(len(history_data)-1, 0, -1):
                for pr in history_data[i]['reds']:
                    for cr in history_data[i-1]['reds']: rt[pr][cr] += 1
                for pb in history_data[i]['blues']:
                    for cb in history_data[i-1]['blues']: bt[pb][cb] += 1
            nr, nb = Counter(), Counter()
            for r in latest['reds']:
                for n, c in rt[r].items(): nr[n] += c
            for b in latest['blues']:
                for n, c in bt[b].items(): nb[n] += c
            return sorted([x[0] for x in nr.most_common(r_pick)]), [x[0] for x in nb.most_common(b_pick)]
        else:
            pt1, pt2, pt3 = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
            for i in range(len(history_data)-1, 0, -1):
                pr, cr = history_data[i]['reds'], history_data[i-1]['reds']
                pt1[pr[0]][cr[0]] += 1
                pt2[pr[1]][cr[1]] += 1
                pt3[pr[2]][cr[2]] += 1
            b1, b2, b3 = latest['reds'][0], latest['reds'][1], latest['reds'][2]
            n1, n2, n3 = pt1[b1].most_common(1), pt2[b2].most_common(1), pt3[b3].most_common(1)
            return (n1[0][0] if n1 else b1), (n2[0][0] if n2 else b2), (n3[0][0] if n3 else b3)

    def fmt_big(name, r, b):
        return f"[{name}]\n红/前: {' '.join(r)}\n蓝/后: {' '.join(b)}\n\n"
    def fmt_sml(name, p1, p2, p3):
        return f"[{name}]\n直选: {p1} | {p2} | {p3}\n\n"

    if "聚合共识" in algo_type:
        out += "🏆 [终极聚合共识统计]\n\n"
        if is_big:
            all_r, all_b = [], []
            r1, b1 = run_multi(); all_r.extend(r1); all_b.extend(b1)
            r2, b2 = run_ga(); all_r.extend(r2); all_b.extend(b2)
            r3, b3 = run_mc(); all_r.extend(r3); all_b.extend(b3)
            r4, b4 = run_apriori(); all_r.extend(r4); all_b.extend(b4)
            r5, b5 = run_markov(); all_r.extend(r5); all_b.extend(b5)
            
            c_r, c_b = Counter(all_r), Counter(all_b)
            best_r = sorted([x[0] for x in c_r.most_common(r_pick)])
            best_b = sorted([x[0] for x in c_b.most_common(b_pick)])
            alt_r = sorted([x[0] for x in c_r.most_common(r_pick * 2)[r_pick:]])
            alt_b_raw = c_b.most_common(b_pick * 2)[b_pick:]
            alt_b = sorted([x[0] for x in (alt_b_raw if alt_b_raw else c_b.most_common(b_pick))])
            
            out += f"🔥 核心共识 (高频交叉):\n红/前: {' '.join(best_r)}\n蓝/后: {' '.join(best_b)}\n\n"
            out += f"🛡️ 防守共识 (次级提取):\n红/前: {' '.join(alt_r)}\n蓝/后: {' '.join(alt_b)}\n\n"
            out += "--- 各独立模型原生结果 ---\n\n"
            out += fmt_big("多维加权", r1, b1) + fmt_big("遗传算法", r2, b2) + fmt_big("蒙特卡洛", r3, b3) + fmt_big("关联规则", r4, b4) + fmt_big("马尔可夫", r5, b5)
        else:
            a1, a2, a3 = [], [], []
            p1,p2,p3 = run_multi(); a1.append(p1); a2.append(p2); a3.append(p3)
            p1,p2,p3 = run_markov(); a1.append(p1); a2.append(p2); a3.append(p3)
            p1,p2,p3 = run_mc(); a1.append(p1); a2.append(p2); a3.append(p3)
            p1,p2,p3 = run_apriori(); a1.append(p1); a2.append(p2); a3.append(p3)
            c1, c2, c3 = Counter(a1), Counter(a2), Counter(a3)
            out += f"🔥 核心共识直选:\n推荐: {c1.most_common(1)[0][0]} | {c2.most_common(1)[0][0]} | {c3.most_common(1)[0][0]}\n\n"
            out += f"🛡️ 防守共识直选:\n推荐: {c1.most_common(2)[-1][0]} | {c2.most_common(2)[-1][0]} | {c3.most_common(2)[-1][0]}\n"
    
    elif "多维加权" in algo_type:
        out += "🌟 [多维特征加权模型]\n\n"
        if is_big: r, b = run_multi(); out += fmt_big("推算结果", r, b)
        else: p1, p2, p3 = run_multi(); out += fmt_sml("推算结果", p1, p2, p3)
    elif "遗传算法" in algo_type:
        out += "🧬 [遗传算法演化模型]\n\n"
        if is_big: r, b = run_ga(); out += fmt_big("超级基因", r, b)
        else: out += "排位玩法请使用其他模型。\n"
    elif "蒙特卡洛" in algo_type:
        out += "🎲 [蒙特卡洛模拟]\n\n"
        if is_big: r, b = run_mc(); out += fmt_big("黄金形态", r, b)
        else: out += "排位玩法请使用其他模型。\n"
    elif "关联规则" in algo_type:
        out += "🔗 [Apriori关联规则挖掘]\n\n"
        if is_big: r, b = run_apriori(); out += fmt_big("伴生组合", r, b)
        else: out += "排位玩法请使用其他模型。\n"
    elif "马尔可夫" in algo_type:
        out += "🔄 [一阶马尔可夫状态转移]\n\n"
        if is_big: r, b = run_markov(); out += fmt_big("概率转移", r, b)
        else: p1, p2, p3 = run_markov(); out += fmt_sml("概率转移", p1, p2, p3)

    return out

# --- 按钮与输出 ---
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🚀 启动 AI 推算", use_container_width=True, type="primary"):
    with st.spinner(f"正在拉取 {lotto_type} 近 {limit} 期数据，AI 模型全速计算中..."):
        try:
            result = fetch_and_calc(lotto_type, limit, algo_type)
            st.code(result, language="text") # 黑客风终端输出框
        except Exception as e:
            st.error(f"网络异常或数据结构变动，报错信息: {e}")
