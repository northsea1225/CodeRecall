"""
seed_oi_mistakes.py — 向 old_user (id=1) 补 12 道 C++ OI 经典错题
+ 对应 ReviewLog 历史，触发 AI 6 阶段教练中的 6 个状态。

Idempotent: title 已存在则跳过，可安全多次运行。

Usage:
    cd backend
    .venv/bin/python -m scripts.seed_oi_mistakes
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.db.session import SessionLocal
from app.models.category import Category
from app.models.mistake import Mistake
from app.models.review import ReviewLog
from app.models.tag import Tag
from app.models.user import User

OLD_USER_ID = 1
SEED_SOURCE = "OI 经典补充 v1"
NOW = datetime.utcnow()


def _log(days_ago: float, result: str) -> dict:
    return {"days_ago": days_ago, "result": result}


MISTAKES: list[dict] = [
    # 1. 二分查找边界 — early_review — d3
    {
        "title": "二分查找 l<=r vs l<r 边界混淆",
        "stem_markdown": (
            "在有序数组中查找目标值，常见有两种二分模板：\n"
            "1. 闭区间 [l, r]：`while (l <= r)`，`r = mid - 1`\n"
            "2. 左闭右开 [l, r)：`while (l < r)`，`r = mid`\n\n"
            "本题混用了两种模板：循环条件用 `l <= r`，但更新用 `r = mid`，"
            "导致 mid 永远在区间内死循环。"
        ),
        "wrong_answer_markdown": (
            "```cpp\n"
            "int lower_bound_buggy(int* a, int n, int target) {\n"
            "  int l = 0, r = n - 1;\n"
            "  while (l <= r) {              // 闭区间循环\n"
            "    int mid = (l + r) >> 1;\n"
            "    if (a[mid] < target) l = mid + 1;\n"
            "    else r = mid;               // ❌ 应该是 r = mid - 1\n"
            "  }\n"
            "  return l;\n"
            "}\n"
            "```\n\n"
            "错点：`r = mid` 让 mid 重新落在 [l, r] 内，永远不能收敛。"
        ),
        "correct_answer_markdown": (
            "```cpp\n"
            "// 方案 1：左闭右开 [l, r)\n"
            "int lower_bound_v1(int* a, int n, int target) {\n"
            "  int l = 0, r = n;\n"
            "  while (l < r) {\n"
            "    int mid = (l + r) >> 1;\n"
            "    if (a[mid] < target) l = mid + 1;\n"
            "    else r = mid;\n"
            "  }\n"
            "  return l;\n"
            "}\n"
            "```"
        ),
        "error_reason_markdown": (
            "**二分模板的两个核心约束必须一致**：\n"
            "- 循环条件（`<=` 还是 `<`）\n"
            "- 区间收缩方式（`r = mid` 还是 `r = mid - 1`）\n\n"
            "记忆口诀：『闭区间用 `<=`，更新用 `mid ± 1`；左闭右开用 `<`，更新用 `mid` 或 `mid + 1`』。\n\n"
            "**最稳的做法**：永远只写一种模板，闭着眼睛背下来。混用是 OI 选手二分翻车的头号原因。"
        ),
        "difficulty": 3,
        "category_name": "算法题",
        "tag_names": ["二分查找"],
        "review_logs": [_log(5, "good")],
        "next_review_offset_days": 1,
    },
    # 2. vector 边遍历边 erase — repeated_weakness — d2
    {
        "title": "vector 边遍历边 erase 导致迭代器失效",
        "stem_markdown": (
            "需要从 vector 中删除所有偶数。用 `for (auto it = v.begin(); it != v.end(); ++it)` 遍历，"
            "命中条件时调 `v.erase(it)`。这导致两个问题：\n\n"
            "1. erase 后迭代器失效，`++it` 是未定义行为\n"
            "2. erase 返回的是下一个有效迭代器，未利用"
        ),
        "wrong_answer_markdown": (
            "```cpp\n"
            "vector<int> v = {1, 2, 3, 4, 5, 6};\n"
            "for (auto it = v.begin(); it != v.end(); ++it) {\n"
            "  if (*it % 2 == 0) {\n"
            "    v.erase(it);  // ❌ it 失效，++it UB\n"
            "  }\n"
            "}\n"
            "```\n\n"
            "错点：erase 后 it 不再有效，后续 ++it 行为未定义；同时 erase 会让后续元素前移，跳过相邻元素。"
        ),
        "correct_answer_markdown": (
            "```cpp\n"
            "// 方案 1：用 erase 的返回值\n"
            "for (auto it = v.begin(); it != v.end(); ) {\n"
            "  if (*it % 2 == 0) {\n"
            "    it = v.erase(it);  // erase 返回下一个有效迭代器\n"
            "  } else {\n"
            "    ++it;\n"
            "  }\n"
            "}\n\n"
            "// 方案 2：erase-remove 惯用法（推荐）\n"
            "v.erase(\n"
            "  remove_if(v.begin(), v.end(), [](int x){ return x % 2 == 0; }),\n"
            "  v.end()\n"
            ");\n"
            "```"
        ),
        "error_reason_markdown": (
            "C++ 标准规定 `vector::erase(it)` 会让 it 和之后所有迭代器失效。\n\n"
            "**正确做法**：\n"
            "- erase 返回新的有效迭代器，**用它**\n"
            "- 命中分支不要 `++it`（因为 erase 已经『推进』了）\n"
            "- 未命中分支才 `++it`\n\n"
            "**更优雅**：使用 `erase-remove` 惯用法，时间复杂度 $O(n)$，比逐个 erase 的 $O(n^2)$ 快得多。"
        ),
        "difficulty": 2,
        "category_name": "STL 陷阱",
        "tag_names": ["STL"],
        "review_logs": [
            _log(2, "hard"),
            _log(7, "again"),
            _log(15, "again"),
        ],
        "next_review_offset_days": -1,
    },
    # 3. unordered_map hash 碰撞退化 — new_mistake — d4
    {
        "title": "unordered_map 被 hack 数据退化为 O(n)",
        "stem_markdown": (
            "CF 上一道哈希题，本地随机数据下 unordered_map 表现完美，"
            "提交后却 TLE。原因是出题人构造了**针对 GCC 默认 hash 函数**的特殊数据，"
            "让所有 key 落到同一个 bucket，单次操作复杂度从 $O(1)$ 退化为 $O(n)$。"
        ),
        "wrong_answer_markdown": (
            "```cpp\n"
            "unordered_map<long long, int> mp;\n"
            "for (int i = 0; i < n; ++i) {\n"
            "  mp[a[i]]++;  // 本地 OK，CF 上 TLE\n"
            "}\n"
            "```\n\n"
            "错点：GCC 的 unordered_map 默认 hash 是 identity（直接返回 key），"
            "出题人可以构造『所有 key 哈希后落同一个槽』的数据，复杂度退化。"
        ),
        "correct_answer_markdown": (
            "```cpp\n"
            "// 方案 1：自定义带随机种子的 hash\n"
            "struct CustomHash {\n"
            "  static uint64_t splitmix64(uint64_t x) {\n"
            "    x += 0x9e3779b97f4a7c15;\n"
            "    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9;\n"
            "    x = (x ^ (x >> 27)) * 0x94d049bb133111eb;\n"
            "    return x ^ (x >> 31);\n"
            "  }\n"
            "  size_t operator()(uint64_t x) const {\n"
            "    static const uint64_t FIXED_RANDOM =\n"
            "      chrono::steady_clock::now().time_since_epoch().count();\n"
            "    return splitmix64(x + FIXED_RANDOM);\n"
            "  }\n"
            "};\n"
            "unordered_map<long long, int, CustomHash> mp;\n\n"
            "// 方案 2：直接用 map（红黑树，稳定 O(log n)）\n"
            "map<long long, int> mp;\n"
            "```"
        ),
        "error_reason_markdown": (
            "GCC 的 `unordered_map` 默认 hash 函数对整数是恒等函数 $h(x) = x$，"
            "并使用模质数的桶分布——这一切都是公开的，出题人可以构造特殊数据让所有 key 模质数同余。\n\n"
            "**应对策略**：\n"
            "1. 加随机种子让 hash 不可预测（splitmix64 是经典做法）\n"
            "2. 复杂度敏感场景直接用 `map`（红黑树），$O(\\log n)$ 但稳定\n"
            "3. 数据范围允许时用数组直接索引\n\n"
            "**Codeforces 名人贴**："
            "[blog: Blowing up unordered_map](https://codeforces.com/blog/entry/62393)"
        ),
        "difficulty": 4,
        "category_name": "STL 陷阱",
        "tag_names": ["STL", "哈希"],
        "review_logs": [],
        "next_review_offset_days": 0,
    },
    # 4. 位运算优先级 — new_mistake — d2
    {
        "title": "位运算 & 优先级低于 == 踩坑",
        "stem_markdown": (
            "判断整数 x 的最低位是否为 1，写成 `if (x & 1 == 1)`。"
            "在 C/C++ 中，`==` 的优先级**高于** `&`，所以表达式被解析为 `x & (1 == 1)` "
            "也就是 `x & 1`，但更隐蔽的是当判断 `x & 2 == 2` 时变成 `x & (2 == 2)` 即 `x & 1`，"
            "**结果与预期完全不同**。"
        ),
        "wrong_answer_markdown": (
            "```cpp\n"
            "int x = 4;  // 二进制 100\n"
            "if (x & 2 == 2) {       // ❌ 实际是 x & (2==2) = x & 1 = 0\n"
            "  cout << \"second bit is 1\";\n"
            "}\n"
            "// 输出：什么都不输出（因为 x & 1 = 0）\n"
            "// 但 x 的第 2 位明明是 1！\n"
            "```"
        ),
        "correct_answer_markdown": (
            "```cpp\n"
            "if ((x & 2) == 2) {     // ✅ 显式加括号\n"
            "  cout << \"second bit is 1\";\n"
            "}\n\n"
            "// 或者直接判非零\n"
            "if (x & 2) {            // ✅ 等价写法\n"
            "  cout << \"second bit is 1\";\n"
            "}\n"
            "```"
        ),
        "error_reason_markdown": (
            "C/C++ 运算符优先级（部分）从高到低：\n"
            "```\n"
            "<<  >>             // 移位\n"
            "<  <=  >  >=       // 关系\n"
            "==  !=             // 相等\n"
            "&                  // 按位与   ← 比 == 低！\n"
            "^                  // 按位异或\n"
            "|                  // 按位或\n"
            "&&                 // 逻辑与\n"
            "||                 // 逻辑或\n"
            "```\n\n"
            "**位运算优先级低于关系运算符**，是 C 语言历史遗留设计（B 语言时期 `==` 还没出现，"
            "后来加上 `==` 时位运算优先级没改）。\n\n"
            "**实战建议**：**位运算永远加括号**，不要相信优先级记忆。"
        ),
        "difficulty": 2,
        "category_name": "算法题",
        "tag_names": ["位运算"],
        "review_logs": [],
        "next_review_offset_days": 0,
    },
    # 5. 浮点比较 EPS — early_review — d2 — LaTeX
    {
        "title": "浮点数直接用 == 比较",
        "stem_markdown": (
            "计算几何中比较两个 double 是否相等：\n\n"
            "```cpp\nif (a == b) ...\n```\n\n"
            "由于浮点数表示精度有限（IEEE 754 双精度只有 52 位尾数），即使数学上相等的两个数，"
            "经过不同计算路径后内部表示可能差一个 ULP。\n\n"
            "**正确做法**：定义足够小的 $\\varepsilon$，判断 $|a - b| < \\varepsilon$。"
        ),
        "wrong_answer_markdown": (
            "```cpp\n"
            "double a = 0.1 + 0.2;\n"
            "double b = 0.3;\n"
            "if (a == b) {  // ❌ false！\n"
            "  cout << \"equal\";\n"
            "}\n"
            "// 实际 a = 0.30000000000000004，b = 0.3，不等\n"
            "```"
        ),
        "correct_answer_markdown": (
            "```cpp\n"
            "const double EPS = 1e-9;\n\n"
            "inline bool eq(double a, double b) {\n"
            "  return fabs(a - b) < EPS;\n"
            "}\n\n"
            "if (eq(a, b)) {  // ✅ true\n"
            "  cout << \"equal\";\n"
            "}\n"
            "```"
        ),
        "error_reason_markdown": (
            "IEEE 754 双精度浮点数（double）的精度约为 $10^{-15}$，但累积运算后误差会放大。\n\n"
            "**比较准则**：\n"
            "$$|a - b| < \\varepsilon$$\n\n"
            "$\\varepsilon$ 的取值：\n"
            "- 计算几何：$10^{-9}$ 到 $10^{-7}$（坐标 $10^4$ 量级）\n"
            "- 概率 DP：$10^{-9}$\n"
            "- 物理模拟：$10^{-6}$\n\n"
            "**更稳健的写法**：相对误差 + 绝对误差混合判断\n"
            "$$|a - b| < \\max(\\varepsilon_{\\text{abs}}, \\varepsilon_{\\text{rel}} \\cdot \\max(|a|, |b|))$$"
        ),
        "difficulty": 2,
        "category_name": "算法题",
        "tag_names": ["计算几何", "数值计算"],
        "review_logs": [_log(3, "hard")],
        "next_review_offset_days": 1,
    },
    # 6. memset 0x3f — maintenance — d1
    {
        "title": "memset 用 0x3f 表示极大值",
        "stem_markdown": (
            "需要把 int 数组初始化为『无穷大』，但 `memset(dp, INT_MAX, sizeof dp)` 不工作。"
            "原因是 memset 按**字节**填充，INT_MAX = 0x7fffffff，memset 会把每个字节都填成 0xff，"
            "结果数组每个 int 是 0xffffffff = -1（补码）。\n\n"
            "正确做法是用 0x3f 填充，每个 int 变成 0x3f3f3f3f ≈ $10^9$，"
            "既足够大又能 `0x3f3f3f3f + 0x3f3f3f3f` 不溢出。"
        ),
        "wrong_answer_markdown": (
            "```cpp\n"
            "int dp[100];\n"
            "memset(dp, INT_MAX, sizeof dp);\n"
            "// ❌ memset 是按字节填充\n"
            "// 每个 byte 变成 INT_MAX & 0xff = 0xff\n"
            "// 整个 int 变成 0xffffffff = -1\n"
            "cout << dp[0];  // 输出 -1，不是 INT_MAX\n"
            "```"
        ),
        "correct_answer_markdown": (
            "```cpp\n"
            "int dp[100];\n"
            "memset(dp, 0x3f, sizeof dp);\n"
            "// ✅ 每个 int 变成 0x3f3f3f3f = 1061109567 ≈ 1e9\n"
            "// 既足够大，又能两数相加不溢出（2e9 < INT_MAX = 2.1e9）\n\n"
            "// 或者用 fill（更明确）\n"
            "fill(dp, dp + 100, INT_MAX / 2);\n"
            "```"
        ),
        "error_reason_markdown": (
            "memset 是字节级操作，只有当**所有字节相同**的常量才能用：\n"
            "- `0`（全 0） → 0\n"
            "- `-1` / `0xff`（全 1） → -1\n"
            "- `0x3f` → 0x3f3f3f3f（约 $10^9$，常用『无穷大』）\n\n"
            "**记忆**：『memset 只填 -1、0、0x3f』，其他值都用 fill 或循环。\n\n"
            "**为什么是 0x3f 不是 0x7f？** 0x3f3f3f3f + 0x3f3f3f3f 不溢出（< INT_MAX），"
            "0x7f7f7f7f + 0x7f7f7f7f 溢出为负数，DP 中很容易出问题。"
        ),
        "difficulty": 1,
        "category_name": "算法题",
        "tag_names": ["小技巧"],
        "review_logs": [
            _log(30, "easy"),
            _log(60, "easy"),
            _log(90, "good"),
            _log(120, "good"),
            _log(150, "good"),
        ],
        "next_review_offset_days": 30,
    },
    # 7. ST 表 lg 预处理 — lapsed — d4
    {
        "title": "ST 表 lg 数组预处理边界错误",
        "stem_markdown": (
            "用 ST 表（Sparse Table）做 RMQ 区间最值，需要预处理 `lg[i] = floor(log2(i))`。"
            "递推式 `lg[i] = lg[i / 2] + 1` 从 i=2 开始，但代码从 i=1 开始且 lg[0] 未初始化，"
            "导致 lg[1] = lg[0] + 1 = 1 + 1 = 2（实际应为 0），后续全错。"
        ),
        "wrong_answer_markdown": (
            "```cpp\n"
            "int lg[N];\n"
            "// 没显式初始化，lg[0] 是栈内随机值\n"
            "for (int i = 1; i < N; ++i) {\n"
            "  lg[i] = lg[i / 2] + 1;  // ❌ i=1 时 lg[0] 未定义\n"
            "}\n"
            "```"
        ),
        "correct_answer_markdown": (
            "```cpp\n"
            "int lg[N];\n"
            "lg[1] = 0;                  // base case: log2(1) = 0\n"
            "for (int i = 2; i < N; ++i) {\n"
            "  lg[i] = lg[i / 2] + 1;\n"
            "}\n\n"
            "// 或者更直接地用 __lg / __builtin_clz\n"
            "// int k = __lg(r - l + 1);  // 等价于 (int)log2(r-l+1)\n"
            "```"
        ),
        "error_reason_markdown": (
            "ST 表查询 [l, r] 区间最值需要 `k = lg[r - l + 1]`，再用 `min(st[l][k], st[r-(1<<k)+1][k])`。\n\n"
            "lg 数组**必须从 i=2 开始递推**，因为：\n"
            "- $\\lfloor \\log_2 1 \\rfloor = 0$（base case，手动赋值）\n"
            "- $\\lfloor \\log_2 i \\rfloor = \\lfloor \\log_2 (i/2) \\rfloor + 1$（递推关系，i ≥ 2）\n\n"
            "**全局数组未初始化时是 0**（C++ 标准保证），但栈上数组是**随机值**——本题如果 lg 在函数内就是栈上，未初始化会随机崩。\n\n"
            "**替代方案**：直接用 GCC 内置 `__lg(x)` 或 `31 - __builtin_clz(x)`，省去预处理。"
        ),
        "difficulty": 4,
        "category_name": "数据结构",
        "tag_names": ["树形数据结构"],
        "review_logs": [_log(60, "again")],
        "next_review_offset_days": -10,
    },
    # 8. 树形 DP 后序遍历漏更新 — oscillator — d3
    {
        "title": "树形 DP 后序遍历漏更新父节点",
        "stem_markdown": (
            "树上最大独立集 DP：`f[u][0]` 表示不选 u 的子树最大独立集，"
            "`f[u][1]` 表示选 u 的子树最大独立集。需要先递归子节点，再用子节点的 f 值更新 u。\n\n"
            "代码递归了子节点，但在 for 循环里**只读取子节点 f 值，没有用它累加到 u 的 f**，"
            "导致 u 的 f 始终是初始值。"
        ),
        "wrong_answer_markdown": (
            "```cpp\n"
            "void dfs(int u, int fa) {\n"
            "  f[u][0] = 0;\n"
            "  f[u][1] = val[u];\n"
            "  for (int v : G[u]) {\n"
            "    if (v == fa) continue;\n"
            "    dfs(v, u);\n"
            "    // ❌ 忘记累加 f[v] 到 f[u]\n"
            "  }\n"
            "}\n"
            "```"
        ),
        "correct_answer_markdown": (
            "```cpp\n"
            "void dfs(int u, int fa) {\n"
            "  f[u][0] = 0;\n"
            "  f[u][1] = val[u];\n"
            "  for (int v : G[u]) {\n"
            "    if (v == fa) continue;\n"
            "    dfs(v, u);\n"
            "    f[u][0] += max(f[v][0], f[v][1]);  // u 不选，v 可选可不选\n"
            "    f[u][1] += f[v][0];                  // u 选，v 必须不选\n"
            "  }\n"
            "}\n"
            "```"
        ),
        "error_reason_markdown": (
            "树形 DP 的『后序遍历』包含两个动作：\n"
            "1. **递归子节点**：保证子节点的 f 计算完毕\n"
            "2. **用子节点 f 更新 u 的 f**：根据状态转移方程合并\n\n"
            "漏掉第 2 步是新手最常见的错误——脑子里『dfs 完就好了』，"
            "但 dfs 只是『下去算』，**回来还得『合上来』**。\n\n"
            "**调试技巧**：树形 DP 写完先用 n=3 的小样例手算一遍 f 值，对比代码输出。"
        ),
        "difficulty": 3,
        "category_name": "算法题",
        "tag_names": ["动态规划", "树形数据结构"],
        "review_logs": [
            _log(3, "good"),
            _log(10, "again"),
            _log(20, "good"),
            _log(30, "again"),
        ],
        "next_review_offset_days": 0,
    },
    # 9. 拓扑排序入度统计 — early_review — d3
    {
        "title": "拓扑排序入度统计漏边",
        "stem_markdown": (
            "用 Kahn 算法做拓扑排序：维护入度数组 in_deg，每条边 (u, v) 让 `in_deg[v]++`。"
            "代码写成在 `dfs/bfs` 过程中才统计入度，导致初始队列只包含一部分 0 入度节点，"
            "结果丢失或顺序错乱。"
        ),
        "wrong_answer_markdown": (
            "```cpp\n"
            "queue<int> q;\n"
            "for (int i = 1; i <= n; ++i) {\n"
            "  if (in_deg[i] == 0) q.push(i);\n"
            "  // ❌ 此时 in_deg 还没填完！\n"
            "}\n"
            "// 边在 dfs 内才扫到\n"
            "while (!q.empty()) {\n"
            "  int u = q.front(); q.pop();\n"
            "  for (int v : G[u]) {\n"
            "    in_deg[v]++;  // ❌ 入队后才统计，逻辑反了\n"
            "    if (--in_deg[v] == 0) q.push(v);\n"
            "  }\n"
            "}\n"
            "```"
        ),
        "correct_answer_markdown": (
            "```cpp\n"
            "// 步骤 1：先扫所有边，统计入度（建图阶段就完成）\n"
            "for (auto [u, v] : edges) {\n"
            "  G[u].push_back(v);\n"
            "  in_deg[v]++;\n"
            "}\n\n"
            "// 步骤 2：把入度为 0 的节点入队\n"
            "queue<int> q;\n"
            "for (int i = 1; i <= n; ++i) {\n"
            "  if (in_deg[i] == 0) q.push(i);\n"
            "}\n\n"
            "// 步骤 3：BFS，每弹出一个节点，减去其出边端点的入度\n"
            "while (!q.empty()) {\n"
            "  int u = q.front(); q.pop();\n"
            "  topo_order.push_back(u);\n"
            "  for (int v : G[u]) {\n"
            "    if (--in_deg[v] == 0) q.push(v);\n"
            "  }\n"
            "}\n"
            "```"
        ),
        "error_reason_markdown": (
            "Kahn 算法的正确步骤：\n"
            "1. **建图时**同步统计所有节点的入度（in_deg）\n"
            "2. **初始化队列**：所有 in_deg = 0 的节点入队\n"
            "3. **BFS**：每次弹出 u，遍历 u 的出边，让端点入度 -1；若降为 0 则入队\n\n"
            "顺序不能错。常见错误：\n"
            "- 在 BFS 内才统计入度（逻辑倒置）\n"
            "- 忘了减少入度（无法触发后续节点入队）\n"
            "- 用 += 而非 --（统计反了）\n\n"
            "**检测环**：BFS 结束后若 `topo_order.size() < n`，说明有环。"
        ),
        "difficulty": 3,
        "category_name": "算法题",
        "tag_names": ["图论"],
        "review_logs": [
            _log(5, "good"),
            _log(12, "hard"),
        ],
        "next_review_offset_days": 2,
    },
    # 10. 状压 DP bitmask 越界 — repeated_weakness — d4
    {
        "title": "状压 DP bitmask 越界与符号扩展",
        "stem_markdown": (
            "状压 DP 中状态用 `int` 表示 bitmask。当 n=20 时还能撑住（$2^{20} = 10^6$），"
            "但 n=31 时 `1 << 31` 在 int 中是**最高位符号位**，得到负数 $-2^{31}$，"
            "后续位运算和数组下标全部错乱。"
        ),
        "wrong_answer_markdown": (
            "```cpp\n"
            "int n = 31;\n"
            "int full = (1 << n) - 1;  // ❌ 1 << 31 在 int 中是 INT_MIN\n"
            "                          // (INT_MIN - 1) = INT_MAX（再次溢出）\n"
            "                          // full 变成 INT_MAX，下标越界\n"
            "int dp[1 << 31];          // ❌ 数组大小不能是负数 / 不能这么大\n"
            "```"
        ),
        "correct_answer_markdown": (
            "```cpp\n"
            "// n ≤ 20 时（典型状压 DP 上限）\n"
            "int n = 20;\n"
            "int full = (1 << n) - 1;  // ✅ 1 << 20 = 1048576，安全\n"
            "vector<int> dp(1 << n);\n\n"
            "// 若 n 较大（很少见，因为 2^n 数组本身就装不下），用 long long\n"
            "long long mask = 1LL << n;  // ✅ 显式 long long 字面量\n"
            "```"
        ),
        "error_reason_markdown": (
            "C++ 中**字面量 1 是 int**，`1 << k` 当 k ≥ 31 时是未定义行为或溢出。\n\n"
            "**规则**：\n"
            "- $k < 31$：`1 << k` 安全，结果是正整数\n"
            "- $k = 31$：`1 << 31` 在 int 中是 INT_MIN（最高位符号位）\n"
            "- $k \\ge 32$：未定义行为\n\n"
            "**用 long long 表达式**：`1LL << k` 或 `(uint64_t)1 << k`，最高支持 63 / 64 位。\n\n"
            "**实战边界**：\n"
            "- 状压 DP 通常 n ≤ 20（$10^6$ 状态，每状态再 $O(n)$ 转移共 $10^7$）\n"
            "- 超过 20 一定要分析复杂度，可能题目意图不是状压"
        ),
        "difficulty": 4,
        "category_name": "算法题",
        "tag_names": ["动态规划", "位运算"],
        "review_logs": [
            _log(2, "hard"),
            _log(6, "again"),
            _log(12, "again"),
        ],
        "next_review_offset_days": -1,
    },
    # 11. 滑动窗口收缩条件 — new_mistake — d2
    {
        "title": "滑动窗口收缩条件写错",
        "stem_markdown": (
            "求最长无重复字符子串。用 right 指针向右扩展窗口，遇到重复字符时收缩 left。"
            "正确做法是**每次只让 left 跳过一个字符，循环收缩到无重复**；但代码写成"
            "`left = pos[c] + 1` 直接跳，当 `pos[c] < left` 时反而**回退了 left**，"
            "得到错误答案。"
        ),
        "wrong_answer_markdown": (
            "```cpp\n"
            "int longest(const string& s) {\n"
            "  map<char, int> pos;\n"
            "  int left = 0, ans = 0;\n"
            "  for (int right = 0; right < s.size(); ++right) {\n"
            "    char c = s[right];\n"
            "    if (pos.count(c)) {\n"
            "      left = pos[c] + 1;  // ❌ 当 pos[c] < left 时，left 反而往回跳\n"
            "    }\n"
            "    pos[c] = right;\n"
            "    ans = max(ans, right - left + 1);\n"
            "  }\n"
            "  return ans;\n"
            "}\n"
            "```\n\n"
            "样例 `abba`：\n"
            "- right=0 (a): pos[a]=0\n"
            "- right=1 (b): pos[b]=1\n"
            "- right=2 (b): left = pos[b]+1 = 2，pos[b]=2 ✓\n"
            "- right=3 (a): left = pos[a]+1 = 1 ❌ left 从 2 跳回到 1！\n"
            "- 错误答案：3，正确答案：2"
        ),
        "correct_answer_markdown": (
            "```cpp\n"
            "int longest(const string& s) {\n"
            "  map<char, int> pos;\n"
            "  int left = 0, ans = 0;\n"
            "  for (int right = 0; right < s.size(); ++right) {\n"
            "    char c = s[right];\n"
            "    if (pos.count(c)) {\n"
            "      left = max(left, pos[c] + 1);  // ✅ 用 max 防止回退\n"
            "    }\n"
            "    pos[c] = right;\n"
            "    ans = max(ans, right - left + 1);\n"
            "  }\n"
            "  return ans;\n"
            "}\n"
            "```"
        ),
        "error_reason_markdown": (
            "滑动窗口的**不变量**：left 单调不递减（窗口左边界只能向右移动）。\n\n"
            "当遇到重复字符 c 时，理论上 left 应跳到 `pos[c] + 1`，但如果 `pos[c] < left`，"
            "说明这个 c 已经在窗口外了，不能让 left 倒退。\n\n"
            "**修正**：`left = max(left, pos[c] + 1)`，确保 left 只增不减。\n\n"
            "**通用模板**：滑动窗口里凡是要更新 left 的地方，都要确保 **left 单调**。"
        ),
        "difficulty": 2,
        "category_name": "算法题",
        "tag_names": ["双指针", "字符串"],
        "review_logs": [],
        "next_review_offset_days": 0,
    },
    # 12. Tarjan SCC low 更新 — lapsed — d5 — LaTeX
    {
        "title": "Tarjan SCC low 数组更新时机错误",
        "stem_markdown": (
            "用 Tarjan 算法求强连通分量（SCC）。low 数组定义为：\n\n"
            "$$\\text{low}[u] = \\min\\{\\text{dfn}[u], "
            "\\min_{(u,v) \\in E_T} \\text{low}[v], "
            "\\min_{(u,v) \\in E_B} \\text{dfn}[v]\\}$$\n\n"
            "其中 $E_T$ 是树边，$E_B$ 是回边。\n\n"
            "**错点**：代码对所有边都用 `low[u] = min(low[u], low[v])`，"
            "包括非树边——这是**错的**，非树边只能用 dfn[v] 更新。"
        ),
        "wrong_answer_markdown": (
            "```cpp\n"
            "void tarjan(int u) {\n"
            "  dfn[u] = low[u] = ++timer;\n"
            "  stk.push(u); in_stack[u] = true;\n"
            "  for (int v : G[u]) {\n"
            "    if (!dfn[v]) {\n"
            "      tarjan(v);\n"
            "      low[u] = min(low[u], low[v]);  // 树边：用 low[v] OK\n"
            "    } else {\n"
            "      low[u] = min(low[u], low[v]);  // ❌ 错！非树边应用 dfn[v]\n"
            "    }\n"
            "  }\n"
            "  // ...\n"
            "}\n"
            "```"
        ),
        "correct_answer_markdown": (
            "```cpp\n"
            "void tarjan(int u) {\n"
            "  dfn[u] = low[u] = ++timer;\n"
            "  stk.push(u); in_stack[u] = true;\n"
            "  for (int v : G[u]) {\n"
            "    if (!dfn[v]) {\n"
            "      // 树边\n"
            "      tarjan(v);\n"
            "      low[u] = min(low[u], low[v]);\n"
            "    } else if (in_stack[v]) {\n"
            "      // 回边（指向栈中节点）\n"
            "      low[u] = min(low[u], dfn[v]);  // ✅ 用 dfn[v]\n"
            "    }\n"
            "    // 横叉边 / 前向边：v 已出栈，跳过\n"
            "  }\n"
            "  if (dfn[u] == low[u]) {\n"
            "    // u 是 SCC 的根，弹栈直到 u 自己\n"
            "    // ...\n"
            "  }\n"
            "}\n"
            "```"
        ),
        "error_reason_markdown": (
            "Tarjan 的核心思想：low[u] 记录 u 通过**仅走树边再走最多一条回边**能到达的最早节点的 dfn。\n\n"
            "- **树边** (u, v)：v 是 u 在 DFS 树上的孩子，low[v] 已计算完，可以传递\n"
            "- **回边** (u, v)：v 是 u 的祖先（在栈中），只能跨一条，所以用 dfn[v] 而不是 low[v]\n"
            "- **横叉边 / 前向边**：v 已经出栈（属于其他 SCC），**直接忽略**\n\n"
            "用 `low[v]` 更新非树边会破坏 low 的定义，导致 SCC 划分错误。\n\n"
            "**判定 SCC 根**：`dfn[u] == low[u]` 时，u 是它所在 SCC 的根，弹栈到 u 即可得到该 SCC。\n\n"
            "**记忆口诀**：『树边传 low，回边传 dfn，横叉前向直接忽略』。"
        ),
        "difficulty": 5,
        "category_name": "算法题",
        "tag_names": ["图论"],
        "review_logs": [
            _log(90, "again"),
            _log(100, "hard"),
        ],
        "next_review_offset_days": -15,
    },
]


def get_or_create_category(db, name: str, description: str = "") -> Category:
    cat = (
        db.query(Category)
        .filter(Category.user_id == OLD_USER_ID, Category.name == name)
        .first()
    )
    if not cat:
        cat = Category(user_id=OLD_USER_ID, name=name, description=description)
        db.add(cat)
        db.flush()
    return cat


def get_or_create_tag(db, name: str) -> Tag:
    tag = (
        db.query(Tag)
        .filter(Tag.user_id == OLD_USER_ID, Tag.name == name)
        .first()
    )
    if not tag:
        tag = Tag(user_id=OLD_USER_ID, name=name)
        db.add(tag)
        db.flush()
    return tag


def main() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == OLD_USER_ID).first()
        if not user:
            print(f"❌ User id={OLD_USER_ID} not found. Abort.")
            return

        before = db.query(Mistake).filter(Mistake.user_id == OLD_USER_ID).count()
        print(f"Before: old_user has {before} mistakes")

        inserted = 0
        skipped = 0

        for spec in MISTAKES:
            # 幂等：title 已存在则跳过
            existing = (
                db.query(Mistake)
                .filter(
                    Mistake.user_id == OLD_USER_ID,
                    Mistake.title == spec["title"],
                )
                .first()
            )
            if existing:
                skipped += 1
                continue

            cat = get_or_create_category(db, spec["category_name"])
            tag_objs = [get_or_create_tag(db, t) for t in spec.get("tag_names", [])]

            logs = spec.get("review_logs", [])
            last_reviewed = (
                NOW - timedelta(days=logs[0]["days_ago"]) if logs else None
            )
            next_review = NOW + timedelta(days=spec.get("next_review_offset_days", 1))

            mistake = Mistake(
                uuid=uuid.uuid4().hex.lower(),
                title=spec["title"],
                user_id=OLD_USER_ID,
                stem_markdown=spec["stem_markdown"],
                wrong_answer_markdown=spec["wrong_answer_markdown"],
                correct_answer_markdown=spec["correct_answer_markdown"],
                error_reason_markdown=spec["error_reason_markdown"],
                language="cpp",
                category_id=cat.id,
                difficulty=spec["difficulty"],
                source=SEED_SOURCE,
                status="new",
                review_count=len(logs),
                last_reviewed_at=last_reviewed,
                next_review_at=next_review,
                ease_factor=2.5,
                interval_days=1,
                repetition=len(logs),
                is_archived=False,
            )
            mistake.tags = []  # 不通过 ORM 关系建立，下面用 raw SQL
            db.add(mistake)
            db.flush()

            # 用 raw SQL 直接 INSERT mistake_tags，避免 ORM 双向同步引起的重复 INSERT
            for tag in tag_objs:
                db.execute(
                    text(
                        "INSERT INTO mistake_tags (mistake_id, tag_id) "
                        "VALUES (:m, :t)"
                    ),
                    {"m": mistake.id, "t": tag.id},
                )

            # ReviewLog 历史（按 days_ago 倒序插入：最早的 log 先插，最近的 log 后插）
            for log_spec in sorted(logs, key=lambda x: -x["days_ago"]):
                shown_at = NOW - timedelta(days=log_spec["days_ago"])
                log = ReviewLog(
                    user_id=OLD_USER_ID,
                    mistake_id=mistake.id,
                    session_id=None,
                    review_mode="spaced_repetition",
                    user_result=log_spec["result"],
                    shown_at=shown_at,
                    answered_at=shown_at + timedelta(seconds=30),
                    old_interval_days=1,
                    new_interval_days=1,
                    old_ease_factor=2.5,
                    new_ease_factor=2.5,
                    time_spent_ms=30000,
                )
                db.add(log)

            inserted += 1

        db.commit()

        after = db.query(Mistake).filter(Mistake.user_id == OLD_USER_ID).count()
        log_total = (
            db.query(ReviewLog)
            .filter(ReviewLog.user_id == OLD_USER_ID)
            .count()
        )
        print(f"After:  old_user has {after} mistakes (+{after - before})")
        print(f"Inserted: {inserted}  Skipped (already existed): {skipped}")
        print(f"Total ReviewLogs for old_user: {log_total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
