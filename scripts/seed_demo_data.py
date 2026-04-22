#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
import os
import json
from pathlib import Path
import sys

from sqlalchemy import delete, func, select, text


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

BACKEND_ENV = BACKEND_DIR / ".env"
if "DATABASE_URL" not in os.environ and BACKEND_ENV.exists():
    for line in BACKEND_ENV.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != "DATABASE_URL":
            continue
        value = value.strip().strip('"').strip("'")
        if value.startswith("sqlite:///./"):
            value = "sqlite:///" + str((BACKEND_DIR / value.removeprefix("sqlite:///./")).resolve())
        os.environ["DATABASE_URL"] = value
        break

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import (
    Category,
    Mistake,
    MistakeStatus,
    MistakeTag,
    ReviewLog,
    ReviewResult,
    ReviewSession,
    ReviewSessionItem,
    Tag,
)


CATEGORY_NAMES = ["算法", "前端", "Python", "数据库", "系统设计", "工程实践"]
TAG_NAMES = [
    "python",
    "javascript",
    "typescript",
    "react",
    "sql",
    "算法",
    "数组",
    "哈希",
    "链表",
    "树",
    "动态规划",
    "异步",
    "闭包",
    "类型系统",
    "索引",
    "事务",
    "设计模式",
    "测试",
]

MODE_QUOTAS = {"React": 168, "Async": 112, "Regex": 56, "CSS": 38}


def utc_now_naive() -> datetime:
    return datetime.utcnow().replace(microsecond=0)


def clear_tables(session) -> None:
    session.execute(delete(ReviewLog))
    session.execute(delete(ReviewSessionItem))
    session.execute(delete(ReviewSession))
    session.execute(delete(MistakeTag))
    session.execute(delete(Mistake))
    session.execute(delete(Tag))
    session.execute(delete(Category))
    session.commit()

    if session.bind and session.bind.dialect.name == "sqlite":
        has_sequence = session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
        ).first()
        if has_sequence is None:
            return
        session.execute(
            text(
                "DELETE FROM sqlite_sequence WHERE name IN "
                "('categories', 'tags', 'mistakes', 'review_logs', "
                "'review_sessions', 'review_session_items')"
            )
        )
        session.commit()


def created_at_for(index: int, now: datetime) -> datetime:
    wave_offsets = [0, 1, 1, 3, 5, 8, 8, 13, 15, 21, 21, 28]
    day_age = min(89, wave_offsets[index % len(wave_offsets)] + (index // len(wave_offsets)) * 14)
    return now - timedelta(days=day_age, hours=(index * 3) % 17, minutes=(index * 11) % 50)


NARRATIVE_PATH = Path(__file__).with_name('mistake_narrative.json')
MISTAKE_NARRATIVE: dict[str, dict[str, str]] = {}
if NARRATIVE_PATH.exists():
    try:
        MISTAKE_NARRATIVE = json.loads(NARRATIVE_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        MISTAKE_NARRATIVE = {}


MISTAKE_CONTENT: dict[str, dict[str, str]] = {
    # ── 算法 ──────────────────────────────────────────────────────────────────
    "两数之和哈希表更新顺序": {
        "wrong": """\
```python
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        seen[num] = i          # 先存，再查——同一个元素可能和自己配对
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
    return []
```""",
        "correct": """\
```python
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:          # 先查再存，避免自配对
            return [seen[complement], i]
        seen[num] = i
    return []
```""",
    },
    "链表反转丢失 next 指针": {
        "wrong": """\
```python
def reverse_list(head):
    prev = None
    curr = head
    while curr:
        curr.next = prev   # 先断链，丢失了 curr.next 的引用
        prev = curr
        curr = curr.next   # curr.next 已经是 None，循环立即终止
    return prev
```""",
        "correct": """\
```python
def reverse_list(head):
    prev = None
    curr = head
    while curr:
        next_node = curr.next   # 先保存下一节点
        curr.next = prev
        prev = curr
        curr = next_node        # 用保存的引用前进
    return prev
```""",
    },
    "二叉树层序遍历队列边界": {
        "wrong": """\
```typescript
function levelOrder(root: TreeNode | null): number[][] {
    if (!root) return [];
    const queue = [root];
    const result: number[][] = [];
    while (queue.length) {
        const level: number[] = [];
        // 错误：用变化中的 queue.length 作为本层边界
        for (let i = 0; i < queue.length; i++) {
            const node = queue.shift()!;
            level.push(node.val);
            if (node.left)  queue.push(node.left);
            if (node.right) queue.push(node.right);
        }
        result.push(level);
    }
    return result;
}
```""",
        "correct": """\
```typescript
function levelOrder(root: TreeNode | null): number[][] {
    if (!root) return [];
    const queue = [root];
    const result: number[][] = [];
    while (queue.length) {
        const size = queue.length;   // 快照本层节点数
        const level: number[] = [];
        for (let i = 0; i < size; i++) {
            const node = queue.shift()!;
            level.push(node.val);
            if (node.left)  queue.push(node.left);
            if (node.right) queue.push(node.right);
        }
        result.push(level);
    }
    return result;
}
```""",
    },
    "动态规划状态转移漏初始化": {
        "wrong": """\
```python
def longest_common_subsequence(text1, text2):
    m, n = len(text1), len(text2)
    dp = [[0] * n for _ in range(m)]   # 缺少第 0 行/列的边界初始化
    for i in range(1, m):
        for j in range(1, n):
            if text1[i] == text2[j]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m-1][n-1]
```""",
        "correct": """\
```python
def longest_common_subsequence(text1, text2):
    m, n = len(text1), len(text2)
    # 多一行一列用于边界 base case，初始值 0
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i-1] == text2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n]
```""",
    },
    "滑动窗口收缩条件过早": {
        "wrong": """\
```javascript
function minSubArrayLen(target, nums) {
    let left = 0, sum = 0, minLen = Infinity;
    for (let right = 0; right < nums.length; right++) {
        sum += nums[right];
        // 只收缩一次，错过更短的窗口
        if (sum >= target) {
            minLen = Math.min(minLen, right - left + 1);
            sum -= nums[left++];
        }
    }
    return minLen === Infinity ? 0 : minLen;
}
```""",
        "correct": """\
```javascript
function minSubArrayLen(target, nums) {
    let left = 0, sum = 0, minLen = Infinity;
    for (let right = 0; right < nums.length; right++) {
        sum += nums[right];
        // 持续收缩，直到窗口不再满足条件
        while (sum >= target) {
            minLen = Math.min(minLen, right - left + 1);
            sum -= nums[left++];
        }
    }
    return minLen === Infinity ? 0 : minLen;
}
```""",
    },
    "递归返回值覆盖子问题结果": {
        "wrong": """\
```python
def max_path_sum(root):
    if root is None:
        return 0
    left  = max_path_sum(root.left)
    right = max_path_sum(root.right)
    # 只返回当前向上的最长路径，忽略跨根路径
    return root.val + max(left, right, 0)

# 调用处直接用返回值，但跨根的最大路径从未被记录
result = max_path_sum(root)
```""",
        "correct": """\
```python
def max_path_sum(root):
    best = [float('-inf')]

    def dfs(node):
        if node is None:
            return 0
        left  = max(dfs(node.left), 0)
        right = max(dfs(node.right), 0)
        # 用全局变量记录经过当前节点的跨根路径
        best[0] = max(best[0], node.val + left + right)
        return node.val + max(left, right)

    dfs(root)
    return best[0]
```""",
    },
    "双指针去重跳过有效元素": {
        "wrong": """\
```typescript
function removeDuplicates(nums: number[]): number {
    let slow = 0;
    for (let fast = 1; fast < nums.length; fast++) {
        if (nums[fast] !== nums[slow]) {
            slow++;             // 先移动 slow
            nums[slow] = nums[fast];
        } else {
            slow++;             // 重复时也移动，导致覆盖有效位置
        }
    }
    return slow + 1;
}
```""",
        "correct": """\
```typescript
function removeDuplicates(nums: number[]): number {
    if (nums.length === 0) return 0;
    let slow = 0;
    for (let fast = 1; fast < nums.length; fast++) {
        if (nums[fast] !== nums[slow]) {
            slow++;
            nums[slow] = nums[fast];   // 只在不重复时写入
        }
        // 重复时 fast 继续前进，slow 不动
    }
    return slow + 1;
}
```""",
    },
    "前缀和下标偏移一位": {
        "wrong": """\
```python
def range_sum_query(nums, queries):
    prefix = [0] * len(nums)
    prefix[0] = nums[0]
    for i in range(1, len(nums)):
        prefix[i] = prefix[i-1] + nums[i]

    results = []
    for left, right in queries:
        # 当 left==0 时，prefix[left-1] 是 prefix[-1]，访问了数组末尾
        results.append(prefix[right] - prefix[left - 1])
    return results
```""",
        "correct": """\
```python
def range_sum_query(nums, queries):
    n = len(nums)
    prefix = [0] * (n + 1)   # 多一个哨兵位，prefix[0] = 0
    for i in range(n):
        prefix[i + 1] = prefix[i] + nums[i]

    results = []
    for left, right in queries:
        # prefix[right+1] - prefix[left] 永远安全
        results.append(prefix[right + 1] - prefix[left])
    return results
```""",
    },
    "拓扑排序入度更新遗漏": {
        "wrong": """\
```typescript
function canFinish(numCourses: number, prerequisites: number[][]): boolean {
    const indegree = new Array(numCourses).fill(0);
    const graph: number[][] = Array.from({length: numCourses}, () => []);
    for (const [a, b] of prerequisites) {
        graph[b].push(a);
        indegree[a]++;
    }
    const queue = indegree.map((d, i) => d === 0 ? i : -1).filter(i => i >= 0);
    let visited = 0;
    while (queue.length) {
        const node = queue.shift()!;
        visited++;
        for (const nei of graph[node]) {
            // 漏掉了将入度减到 0 的邻居加入队列
            indegree[nei]--;
        }
    }
    return visited === numCourses;
}
```""",
        "correct": """\
```typescript
function canFinish(numCourses: number, prerequisites: number[][]): boolean {
    const indegree = new Array(numCourses).fill(0);
    const graph: number[][] = Array.from({length: numCourses}, () => []);
    for (const [a, b] of prerequisites) {
        graph[b].push(a);
        indegree[a]++;
    }
    const queue = indegree.map((d, i) => d === 0 ? i : -1).filter(i => i >= 0);
    let visited = 0;
    while (queue.length) {
        const node = queue.shift()!;
        visited++;
        for (const nei of graph[node]) {
            indegree[nei]--;
            if (indegree[nei] === 0) queue.push(nei);  // 补上入队条件
        }
    }
    return visited === numCourses;
}
```""",
    },
    "区间合并排序键选错": {
        "wrong": """\
```python
def merge_intervals(intervals):
    # 按区间结束值排序，导致重叠判断出错
    intervals.sort(key=lambda x: x[1])
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][0]:   # 与 start 比较逻辑也错了
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
```""",
        "correct": """\
```python
def merge_intervals(intervals):
    # 按区间起始值排序是正确做法
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:          # 与上一区间的结束值比较
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
```""",
    },

    # ── 前端 ──────────────────────────────────────────────────────────────────
    "React effect 依赖数组漏填": {
        "wrong": """\
```javascript
function UserProfile({ userId }) {
    const [user, setUser] = useState(null);

    useEffect(() => {
        fetch(`/api/users/${userId}`)
            .then(r => r.json())
            .then(setUser);
    }, []); // 漏填 userId，userId 变化时不会重新请求

    return <div>{user?.name}</div>;
}
```""",
        "correct": """\
```javascript
function UserProfile({ userId }) {
    const [user, setUser] = useState(null);

    useEffect(() => {
        let cancelled = false;
        fetch(`/api/users/${userId}`)
            .then(r => r.json())
            .then(data => { if (!cancelled) setUser(data); });
        return () => { cancelled = true; };
    }, [userId]); // 正确填入依赖，userId 变化时重新请求

    return <div>{user?.name}</div>;
}
```""",
    },
    "React key 使用数组下标导致复用错乱": {
        "wrong": """\
```typescript
function TodoList({ items }: { items: Todo[] }) {
    return (
        <ul>
            {items.map((item, index) => (
                // key=index：删除中间项时，后续组件 state 错位
                <TodoItem key={index} todo={item} />
            ))}
        </ul>
    );
}
```""",
        "correct": """\
```typescript
function TodoList({ items }: { items: Todo[] }) {
    return (
        <ul>
            {items.map(item => (
                // key 使用稳定的业务 ID，React 能正确追踪组件身份
                <TodoItem key={item.id} todo={item} />
            ))}
        </ul>
    );
}
```""",
    },
    "受控输入 value 与 onChange 不匹配": {
        "wrong": """\
```javascript
function SearchBox() {
    const [query, setQuery] = useState('');

    return (
        <input
            value={query}
            // 没有传 onChange，React 将输入框锁死为受控只读
            placeholder="搜索..."
        />
    );
}
```""",
        "correct": """\
```javascript
function SearchBox() {
    const [query, setQuery] = useState('');

    return (
        <input
            value={query}
            onChange={e => setQuery(e.target.value)}  // 必须同步更新 state
            placeholder="搜索..."
        />
    );
}
```""",
    },
    "CSS flex 子项收缩导致按钮溢出": {
        "wrong": """\
```typescript
// 样式以 inline style 表示（等价 CSS）
function Toolbar() {
    return (
        <div style={{ display: 'flex' }}>
            <input style={{ flexGrow: 1 }} placeholder="搜索" />
            {/* 按钮默认 flex-shrink:1，被 input 挤压到 0 宽 */}
            <button>提交</button>
        </div>
    );
}
```""",
        "correct": """\
```typescript
function Toolbar() {
    return (
        <div style={{ display: 'flex' }}>
            <input style={{ flexGrow: 1, minWidth: 0 }} placeholder="搜索" />
            {/* flexShrink:0 防止按钮被压缩 */}
            <button style={{ flexShrink: 0 }}>提交</button>
        </div>
    );
}
```""",
    },
    "Promise 链异常没有返回": {
        "wrong": """\
```javascript
function loadUserData(userId) {
    return fetch(`/api/users/${userId}`)
        .then(response => {
            if (!response.ok) {
                // 没有 return，后续 .then 拿到 undefined 而非 rejected promise
                Promise.reject(new Error(`HTTP ${response.status}`));
            }
            return response.json();
        })
        .then(data => processUser(data));
}
```""",
        "correct": """\
```javascript
function loadUserData(userId) {
    return fetch(`/api/users/${userId}`)
        .then(response => {
            if (!response.ok) {
                // return 确保 reject 传递到 catch
                return Promise.reject(new Error(`HTTP ${response.status}`));
            }
            return response.json();
        })
        .then(data => processUser(data))
        .catch(err => { console.error('loadUserData failed:', err); throw err; });
}
```""",
    },
    "闭包读取旧状态导致计数跳变": {
        "wrong": """\
```javascript
function Counter() {
    const [count, setCount] = useState(0);

    function handleTripleClick() {
        // 三次调用读到同一个闭包里的 count，结果只 +1
        setCount(count + 1);
        setCount(count + 1);
        setCount(count + 1);
    }

    return <button onClick={handleTripleClick}>{count}</button>;
}
```""",
        "correct": """\
```javascript
function Counter() {
    const [count, setCount] = useState(0);

    function handleTripleClick() {
        // 函数式更新，每次拿到最新 state
        setCount(prev => prev + 1);
        setCount(prev => prev + 1);
        setCount(prev => prev + 1);
    }

    return <button onClick={handleTripleClick}>{count}</button>;
}
```""",
    },
    "TypeScript props 可选字段未收窄": {
        "wrong": """\
```typescript
interface CardProps {
    title: string;
    subtitle?: string;
}

function Card({ title, subtitle }: CardProps) {
    // subtitle 可能是 undefined，直接调用方法会报错
    return (
        <div>
            <h2>{title}</h2>
            <p>{subtitle.toUpperCase()}</p>
        </div>
    );
}
```""",
        "correct": """\
```typescript
interface CardProps {
    title: string;
    subtitle?: string;
}

function Card({ title, subtitle }: CardProps) {
    return (
        <div>
            <h2>{title}</h2>
            {/* 先收窄再使用，或提供默认值 */}
            {subtitle && <p>{subtitle.toUpperCase()}</p>}
        </div>
    );
}
```""",
    },
    "列表筛选条件大小写不一致": {
        "wrong": """\
```typescript
function filterProducts(products: Product[], keyword: string) {
    // 用户输入可能是大写，product.name 是混合大小写，直接 includes 匹配失败
    return products.filter(p => p.name.includes(keyword));
}

// 调用
const result = filterProducts(products, 'APPLE'); // 匹配不到 "Apple"
```""",
        "correct": """\
```typescript
function filterProducts(products: Product[], keyword: string) {
    const lower = keyword.toLowerCase();
    return products.filter(p => p.name.toLowerCase().includes(lower));
}

// 调用
const result = filterProducts(products, 'APPLE'); // 正确匹配 "Apple"
```""",
    },
    "正则校验把全局标记状态带入表单": {
        "wrong": """\
```javascript
// 模块级别带 /g 的正则，lastIndex 会在多次调用间保留
const emailRe = /^[\\w.+-]+@[\\w-]+\\.[a-z]{2,}$/gi;

function validateEmail(email) {
    // 第二次调用时 lastIndex 可能非 0，test() 返回错误结果
    return emailRe.test(email);
}

validateEmail('a@b.com'); // true
validateEmail('a@b.com'); // false（lastIndex 状态污染）
```""",
        "correct": """\
```javascript
// 不使用 /g 标记，或在函数内创建正则（每次 lastIndex 从 0 开始）
function validateEmail(email) {
    const emailRe = /^[\\w.+-]+@[\\w-]+\\.[a-z]{2,}$/i;
    return emailRe.test(email);
}

validateEmail('a@b.com'); // true
validateEmail('a@b.com'); // true
```""",
    },
    "异步请求取消后仍然 setState": {
        "wrong": """\
```typescript
function useUser(userId: string) {
    const [user, setUser] = useState<User | null>(null);

    useEffect(() => {
        fetchUser(userId).then(data => {
            // 组件已卸载，仍然 setState，造成内存泄漏警告
            setUser(data);
        });
    }, [userId]);

    return user;
}
```""",
        "correct": """\
```typescript
function useUser(userId: string) {
    const [user, setUser] = useState<User | null>(null);

    useEffect(() => {
        const controller = new AbortController();
        fetchUser(userId, { signal: controller.signal })
            .then(data => setUser(data))
            .catch(err => { if (err.name !== 'AbortError') throw err; });
        return () => controller.abort();  // 清理：取消请求
    }, [userId]);

    return user;
}
```""",
    },

    # ── Python ────────────────────────────────────────────────────────────────
    "Python 可变默认参数复用": {
        "wrong": """\
```python
def append_to(element, target=[]):   # target 只初始化一次，跨调用共享
    target.append(element)
    return target

print(append_to(1))  # [1]
print(append_to(2))  # [1, 2]  ← 预期 [2]
```""",
        "correct": """\
```python
def append_to(element, target=None):
    if target is None:
        target = []          # 每次调用创建新列表
    target.append(element)
    return target

print(append_to(1))  # [1]
print(append_to(2))  # [2]
```""",
    },
    "生成器耗尽后重复遍历为空": {
        "wrong": """\
```python
def read_numbers(path):
    with open(path) as f:
        for line in f:
            yield int(line.strip())

gen = read_numbers('data.txt')
total  = sum(gen)      # 耗尽生成器
count  = sum(1 for _ in gen)  # 0，生成器已空
average = total / count       # ZeroDivisionError
```""",
        "correct": """\
```python
def read_numbers(path):
    with open(path) as f:
        for line in f:
            yield int(line.strip())

# 方案：只遍历一次，或转为列表
numbers = list(read_numbers('data.txt'))
total   = sum(numbers)
count   = len(numbers)
average = total / count if count else 0
```""",
    },
    "字典遍历时删除键触发运行时错误": {
        "wrong": """\
```python
def remove_inactive(users: dict):
    for user_id, info in users.items():   # 遍历视图
        if not info['active']:
            del users[user_id]            # 修改字典大小 → RuntimeError
```""",
        "correct": """\
```python
def remove_inactive(users: dict):
    # 先收集要删除的键，再统一删除
    to_delete = [uid for uid, info in users.items() if not info['active']]
    for uid in to_delete:
        del users[uid]
```""",
    },
    "asyncio gather 异常传播误判": {
        "wrong": """\
```python
import asyncio

async def fetch(url):
    ...  # 可能抛出异常

async def main():
    results = await asyncio.gather(
        fetch('https://a.com'),
        fetch('https://b.com'),
        fetch('https://c.com'),
    )
    # 任何一个 coroutine 抛出异常，gather 会立即重新抛出
    # 其余 coroutine 的结果被丢弃，且无法分辨哪个失败
    for r in results:
        process(r)
```""",
        "correct": """\
```python
import asyncio

async def fetch(url):
    ...

async def main():
    results = await asyncio.gather(
        fetch('https://a.com'),
        fetch('https://b.com'),
        fetch('https://c.com'),
        return_exceptions=True,   # 异常作为结果返回，不中断其他任务
    )
    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            print(f'{url} failed: {result}')
        else:
            process(result)
```""",
    },
    "闭包 late binding 捕获循环变量": {
        "wrong": """\
```python
funcs = []
for i in range(5):
    funcs.append(lambda: i)   # 所有 lambda 都引用同一个 i

results = [f() for f in funcs]
print(results)  # [4, 4, 4, 4, 4]，预期 [0, 1, 2, 3, 4]
```""",
        "correct": """\
```python
funcs = []
for i in range(5):
    # 默认参数在定义时求值，捕获当前 i 的值
    funcs.append(lambda i=i: i)

results = [f() for f in funcs]
print(results)  # [0, 1, 2, 3, 4]
```""",
    },
    "装饰器没有保留函数元信息": {
        "wrong": """\
```python
def timer(func):
    def wrapper(*args, **kwargs):
        import time
        start = time.time()
        result = func(*args, **kwargs)
        print(f'耗时 {time.time()-start:.3f}s')
        return result
    return wrapper   # wrapper 覆盖了 func 的 __name__、__doc__

@timer
def compute(n):
    \"\"\"计算平方。\"\"\"
    return n ** 2

print(compute.__name__)  # 'wrapper'，调试困难
```""",
        "correct": """\
```python
import functools

def timer(func):
    @functools.wraps(func)       # 保留原函数的元信息
    def wrapper(*args, **kwargs):
        import time
        start = time.time()
        result = func(*args, **kwargs)
        print(f'耗时 {time.time()-start:.3f}s')
        return result
    return wrapper

@timer
def compute(n):
    \"\"\"计算平方。\"\"\"
    return n ** 2

print(compute.__name__)  # 'compute'
print(compute.__doc__)   # '计算平方。'
```""",
    },
    "列表切片浅拷贝误改嵌套对象": {
        "wrong": """\
```python
matrix = [[1, 2], [3, 4], [5, 6]]
copy   = matrix[:]    # 浅拷贝，内层列表共享

copy[0][0] = 99       # 同时修改了 matrix[0][0]
print(matrix[0])      # [99, 2]，预期 [1, 2]
```""",
        "correct": """\
```python
import copy

matrix = [[1, 2], [3, 4], [5, 6]]
deep_copy = copy.deepcopy(matrix)   # 深拷贝，完全独立

deep_copy[0][0] = 99
print(matrix[0])      # [1, 2]，原始数据不受影响
```""",
    },
    "上下文管理器异常吞掉返回值": {
        "wrong": """\
```python
class SuppressAll:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, tb):
        return True   # 无条件吞掉异常，包括不应吞掉的 SystemExit/KeyboardInterrupt

with SuppressAll():
    x = int('not_a_number')  # ValueError 被静默
    process(x)               # x 未定义，此行不执行但调用方无感知
```""",
        "correct": """\
```python
class SuppressValueError:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, tb):
        # 只吞掉预期的异常类型
        if exc_type is ValueError:
            return True
        return False  # 其他异常（含 SystemExit）正常传播

with SuppressValueError():
    x = int('not_a_number')
```""",
    },
    "正则分组贪婪匹配吞掉边界": {
        "wrong": """\
```python
import re

html = '<b>bold</b> and <i>italic</i>'
# 贪婪 .+ 跨越多个标签，匹配到最后一个 </...>
matches = re.findall(r'<.+>', html)
print(matches)  # ['<b>bold</b> and <i>italic</i>']
```""",
        "correct": """\
```python
import re

html = '<b>bold</b> and <i>italic</i>'
# 改用非贪婪 .+? 或精确字符集
matches = re.findall(r'<.+?>', html)
print(matches)  # ['<b>', '</b>', '<i>', '</i>']
```""",
    },
    "类型注解 Optional 分支未处理": {
        "wrong": """\
```python
from typing import Optional

def get_username(user_id: int) -> Optional[str]:
    ...  # 返回 str 或 None

def greet(user_id: int) -> str:
    name = get_username(user_id)
    # name 可能是 None，直接拼接会抛 TypeError
    return 'Hello, ' + name
```""",
        "correct": """\
```python
from typing import Optional

def get_username(user_id: int) -> Optional[str]:
    ...

def greet(user_id: int) -> str:
    name = get_username(user_id)
    if name is None:               # 显式处理 None 分支
        return 'Hello, Guest'
    return 'Hello, ' + name
```""",
    },

    # ── 数据库 ────────────────────────────────────────────────────────────────
    "SQL JOIN 条件写在 WHERE 导致行丢失": {
        "wrong": """\
```sql
-- 想保留所有 orders，关联可选的 coupon 信息
SELECT o.id, o.amount, c.code
FROM orders o
LEFT JOIN coupons c ON o.coupon_id = c.id
WHERE c.expired = 0;   -- 这里过滤掉了没有 coupon 的行（c.* 为 NULL）
```""",
        "correct": """\
```sql
-- 把过滤条件放进 ON 子句，只影响 JOIN 结果，不丢弃主表行
SELECT o.id, o.amount, c.code
FROM orders o
LEFT JOIN coupons c ON o.coupon_id = c.id AND c.expired = 0;
```""",
    },
    "索引最左前缀没有命中": {
        "wrong": """\
```sql
-- 联合索引 (user_id, created_at, status)
-- 查询跳过 user_id，直接用 created_at，索引失效
SELECT *
FROM orders
WHERE created_at >= '2024-01-01'
  AND status = 'paid';
```""",
        "correct": """\
```sql
-- 遵守最左前缀规则，从 user_id 开始
SELECT *
FROM orders
WHERE user_id = 42
  AND created_at >= '2024-01-01'
  AND status = 'paid';

-- 若确实需要按时间全表查，单独建 (created_at, status) 索引
CREATE INDEX idx_orders_time_status ON orders(created_at, status);
```""",
    },
    "事务隔离级别误读不可重复读": {
        "wrong": """\
```sql
-- 默认 READ COMMITTED，同一事务内两次 SELECT 可能得到不同结果
BEGIN;
SELECT balance FROM accounts WHERE id = 1;  -- 返回 1000
-- 此时另一事务提交了扣款
SELECT balance FROM accounts WHERE id = 1;  -- 返回 800，不可重复读
COMMIT;
```""",
        "correct": """\
```sql
-- 提升到 REPEATABLE READ，保证同一事务内读取一致
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
BEGIN;
SELECT balance FROM accounts WHERE id = 1;  -- 返回 1000
-- 其他事务提交不影响本事务的读视图
SELECT balance FROM accounts WHERE id = 1;  -- 仍然 1000
COMMIT;
```""",
    },
    "分页 offset 大导致慢查询": {
        "wrong": """\
```sql
-- OFFSET 100000 需要扫描并丢弃 10 万行，随页数增大性能急剧下降
SELECT id, title, created_at
FROM articles
ORDER BY created_at DESC
LIMIT 20 OFFSET 100000;
```""",
        "correct": """\
```sql
-- Keyset Pagination：用上一页最后一行的游标值替代 OFFSET
-- 前端传入上一页最后的 (created_at, id)
SELECT id, title, created_at
FROM articles
WHERE (created_at, id) < ('2024-03-01 12:00:00', 54321)
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- 确保 (created_at, id) 有复合索引
CREATE INDEX idx_articles_cursor ON articles(created_at DESC, id DESC);
```""",
    },
    "聚合 HAVING 与 WHERE 混用": {
        "wrong": """\
```sql
-- 错误：将聚合过滤条件放在 WHERE 中，执行时聚合函数尚未计算
SELECT user_id, COUNT(*) AS order_count
FROM orders
WHERE COUNT(*) > 5        -- 语法错误或语义错误
GROUP BY user_id;
```""",
        "correct": """\
```sql
-- WHERE 过滤原始行，HAVING 过滤聚合结果
SELECT user_id, COUNT(*) AS order_count
FROM orders
WHERE status = 'completed'   -- 可以用 WHERE 过滤非聚合列
GROUP BY user_id
HAVING COUNT(*) > 5;         -- 聚合后过滤
```""",
    },
    "唯一约束冲突重试不幂等": {
        "wrong": """\
```sql
-- 重试时直接 INSERT，唯一约束再次抛出错误
INSERT INTO user_points (user_id, event_id, points)
VALUES (42, 'evt_001', 100);
-- 网络超时后重试，同样的行再次插入 → UniqueViolation
```""",
        "correct": """\
```sql
-- 使用 INSERT ... ON CONFLICT DO NOTHING 实现幂等写入
INSERT INTO user_points (user_id, event_id, points)
VALUES (42, 'evt_001', 100)
ON CONFLICT (user_id, event_id) DO NOTHING;

-- 或者需要更新时
INSERT INTO user_points (user_id, event_id, points)
VALUES (42, 'evt_001', 100)
ON CONFLICT (user_id, event_id)
DO UPDATE SET points = EXCLUDED.points,
             updated_at = NOW();
```""",
    },
    "N+1 查询隐藏在序列化层": {
        "wrong": """\
```python
# SQLAlchemy ORM，序列化时触发 N+1
from app.models import Order

def get_orders_with_items(session):
    orders = session.query(Order).all()   # 1 次查询
    return [
        {
            'id': o.id,
            # 访问懒加载关系，每个 order 触发 1 次额外查询
            'items': [{'sku': i.sku} for i in o.items],
        }
        for o in orders
    ]
```""",
        "correct": """\
```python
from sqlalchemy.orm import joinedload
from app.models import Order

def get_orders_with_items(session):
    # 使用 joinedload 或 selectinload 预加载关联数据
    orders = (
        session.query(Order)
        .options(joinedload(Order.items))   # 1 次 JOIN 查询
        .all()
    )
    return [
        {
            'id': o.id,
            'items': [{'sku': i.sku} for i in o.items],  # 无额外查询
        }
        for o in orders
    ]
```""",
    },
    "迁移脚本默认值没有回填历史数据": {
        "wrong": """\
```sql
-- 只添加列和默认值，历史行的该列仍然是 NULL
ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;

-- 应用代码假设 is_verified 不为 NULL，查询结果不符合预期
SELECT * FROM users WHERE is_verified = FALSE;  -- 漏掉历史用户
```""",
        "correct": """\
```sql
-- 步骤 1：添加列，允许 NULL（大表 ALTER 更快）
ALTER TABLE users ADD COLUMN is_verified BOOLEAN;

-- 步骤 2：回填历史数据（分批避免长事务锁表）
UPDATE users SET is_verified = FALSE WHERE is_verified IS NULL;

-- 步骤 3：补充约束
ALTER TABLE users ALTER COLUMN is_verified SET NOT NULL;
ALTER TABLE users ALTER COLUMN is_verified SET DEFAULT FALSE;
```""",
    },
    "锁等待超时没有回滚事务": {
        "wrong": """\
```sql
BEGIN;
UPDATE inventory SET stock = stock - 1 WHERE product_id = 99;
-- 等待锁超时，抛出 LockWaitTimeout 错误
-- 应用层只捕获异常但没有 ROLLBACK，事务处于 aborted 状态
-- 后续同一连接的 SQL 全部失败
UPDATE orders SET status = 'confirmed' WHERE id = 123;
COMMIT;
```""",
        "correct": """\
```sql
BEGIN;
UPDATE inventory SET stock = stock - 1 WHERE product_id = 99;
-- 在应用层捕获异常时必须 ROLLBACK
-- Python 示例（伪代码）:
--   except LockWaitTimeout:
--       conn.execute('ROLLBACK')
--       raise RetryableError()
UPDATE orders SET status = 'confirmed' WHERE id = 123;
COMMIT;
-- 正确做法：超时后 ROLLBACK，重试或向上抛出
```""",
    },
    "JSON 字段查询没有表达式索引": {
        "wrong": """\
```sql
-- metadata 是 JSONB 列，直接查询走全表扫描
SELECT * FROM events
WHERE metadata->>'user_id' = '42';

-- EXPLAIN 显示 Seq Scan，百万行时极慢
```""",
        "correct": """\
```sql
-- 为常用的 JSONB 表达式建索引
CREATE INDEX idx_events_user_id
    ON events ((metadata->>'user_id'));

-- 现在查询可以走 Index Scan
SELECT * FROM events
WHERE metadata->>'user_id' = '42';

-- EXPLAIN 显示 Index Scan using idx_events_user_id
```""",
    },

    # ── 系统设计 ──────────────────────────────────────────────────────────────
    "缓存穿透没有空值缓存": {
        "wrong": """\
```python
def get_product(product_id: int):
    cached = redis.get(f'product:{product_id}')
    if cached:
        return json.loads(cached)

    product = db.query(Product).filter_by(id=product_id).first()
    if product:
        redis.setex(f'product:{product_id}', 3600, json.dumps(product.to_dict()))
    # 不存在时不缓存，每次请求都穿透到数据库
    return product
```""",
        "correct": """\
```python
_NONE_SENTINEL = '__none__'

def get_product(product_id: int):
    cached = redis.get(f'product:{product_id}')
    if cached is not None:
        if cached == _NONE_SENTINEL:
            return None   # 空值命中缓存
        return json.loads(cached)

    product = db.query(Product).filter_by(id=product_id).first()
    if product:
        redis.setex(f'product:{product_id}', 3600, json.dumps(product.to_dict()))
    else:
        redis.setex(f'product:{product_id}', 60, _NONE_SENTINEL)  # 缓存空值 60s
    return product
```""",
    },
    "限流 key 维度选错导致误伤租户": {
        "wrong": """\
```typescript
// 用 IP 作为限流 key，同一 NAT 下的所有租户共享配额
async function rateLimit(req: Request): Promise<boolean> {
    const key = `rate:${req.ip}`;
    const count = await redis.incr(key);
    if (count === 1) await redis.expire(key, 60);
    return count <= 100;
}
```""",
        "correct": """\
```typescript
// 用租户 ID 作为限流 key，隔离不同租户的配额
async function rateLimit(req: Request): Promise<boolean> {
    const tenantId = req.headers['x-tenant-id'] ?? req.ip;
    const key = `rate:${tenantId}`;
    const count = await redis.incr(key);
    if (count === 1) await redis.expire(key, 60);
    if (count > 100) {
        // 返回标准 429，携带重置时间头
        return false;
    }
    return true;
}
```""",
    },
    "消息队列重试缺少幂等键": {
        "wrong": """\
```python
def handle_payment_event(message: dict):
    order_id = message['order_id']
    amount   = message['amount']
    # 网络超时后消息被重投，没有幂等检查，导致重复扣款
    db.execute(
        'INSERT INTO payments (order_id, amount) VALUES (?, ?)',
        (order_id, amount)
    )
    db.commit()
```""",
        "correct": """\
```python
def handle_payment_event(message: dict):
    order_id   = message['order_id']
    amount     = message['amount']
    idempotent_key = message['idempotent_key']  # 消息生产者必须提供

    exists = db.scalar(
        'SELECT 1 FROM payments WHERE idempotent_key = ?', (idempotent_key,)
    )
    if exists:
        return   # 已处理，幂等跳过

    db.execute(
        'INSERT INTO payments (order_id, amount, idempotent_key) VALUES (?, ?, ?)',
        (order_id, amount, idempotent_key)
    )
    db.commit()
```""",
    },
    "读写分离延迟导致读己之写失败": {
        "wrong": """\
```sql
-- 写入主库
INSERT INTO user_profiles (user_id, bio) VALUES (42, 'hello');

-- 立刻从从库读取（主从延迟可能 100ms-1s）
-- 结果：bio 仍为旧值，用户以为保存失败
SELECT bio FROM user_profiles WHERE user_id = 42;  -- 从从库执行
```""",
        "correct": """\
```sql
-- 方案：写后读走主库（Read-Your-Writes 保证）
-- 应用层伪代码：

-- 1. 写主库
INSERT INTO user_profiles (user_id, bio) VALUES (42, 'hello');

-- 2. 立即读也走主库（同一事务或 session 黏主库）
SELECT bio FROM user_profiles WHERE user_id = 42;  -- 强制走主库

-- 或：写入后在 session 中设置 "use_primary" 标记，持续 1-2s
```""",
    },
    "分布式锁过期时间覆盖长任务": {
        "wrong": """\
```python
import redis, time

r = redis.Redis()

def process_order(order_id):
    lock_key = f'lock:order:{order_id}'
    # 锁 TTL 10s，但任务可能耗时 30s
    acquired = r.set(lock_key, '1', nx=True, ex=10)
    if not acquired:
        raise Exception('锁被占用')

    try:
        time.sleep(25)   # 模拟长任务，锁在第 10s 已自动释放
        do_work(order_id)
    finally:
        r.delete(lock_key)   # 可能删掉别人的锁
```""",
        "correct": """\
```python
import redis, threading, uuid, time

r = redis.Redis()

def process_order(order_id):
    lock_key = f'lock:order:{order_id}'
    token = str(uuid.uuid4())
    acquired = r.set(lock_key, token, nx=True, ex=30)
    if not acquired:
        raise Exception('锁被占用')

    stop_event = threading.Event()

    def renew_lock():
        while not stop_event.wait(10):       # 每 10s 续期一次
            r.expire(lock_key, 30)

    t = threading.Thread(target=renew_lock, daemon=True)
    t.start()
    try:
        do_work(order_id)
    finally:
        stop_event.set()
        # 使用 Lua 脚本确保只删自己的锁
        r.eval("if redis.call('get',KEYS[1])==ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end",
               1, lock_key, token)
```""",
    },
    "接口版本兼容字段直接删除": {
        "wrong": """\
```typescript
// v1 响应包含 fullName
interface UserResponseV1 {
    id: number;
    fullName: string;   // 直接删除，破坏旧客户端
}

// v2 直接修改同一接口，移除 fullName
interface UserResponse {
    id: number;
    firstName: string;
    lastName: string;
}
```""",
        "correct": """\
```typescript
// 保留旧字段（标记 deprecated），同时添加新字段
interface UserResponse {
    id: number;
    /** @deprecated 使用 firstName + lastName */
    fullName?: string;
    firstName: string;
    lastName: string;
}

// 服务端同时返回两套字段，给客户端迁移窗口（通常 2 个版本周期）
function toUserResponse(user: User): UserResponse {
    return {
        id: user.id,
        fullName: `${user.firstName} ${user.lastName}`,  // 兼容旧客户端
        firstName: user.firstName,
        lastName: user.lastName,
    };
}
```""",
    },
    "批处理任务没有断点续跑": {
        "wrong": """\
```python
def migrate_users():
    users = db.query('SELECT * FROM legacy_users')
    for user in users:
        new_id = transform_and_insert(user)   # 耗时操作
    print('迁移完成')

# 任务在第 50000 条崩溃，重启后从头开始，重复处理前 50000 条
```""",
        "correct": """\
```python
CHECKPOINT_FILE = '/tmp/migrate_checkpoint.txt'

def get_last_processed_id() -> int:
    if os.path.exists(CHECKPOINT_FILE):
        return int(open(CHECKPOINT_FILE).read().strip())
    return 0

def save_checkpoint(last_id: int):
    open(CHECKPOINT_FILE, 'w').write(str(last_id))

def migrate_users():
    last_id = get_last_processed_id()
    users = db.query('SELECT * FROM legacy_users WHERE id > ? ORDER BY id', (last_id,))
    for user in users:
        transform_and_insert(user)
        if user['id'] % 1000 == 0:
            save_checkpoint(user['id'])   # 每 1000 条保存一次检查点
    print('迁移完成')
```""",
    },
    "告警阈值只看均值漏掉长尾": {
        "wrong": """\
```python
import statistics

def check_latency_alert(latencies_ms: list[float]) -> bool:
    avg = statistics.mean(latencies_ms)
    # 均值 150ms 达标，但 P99 可能是 2000ms
    if avg > 500:
        send_alert(f'平均延迟过高: {avg:.0f}ms')
        return True
    return False
```""",
        "correct": """\
```python
import statistics

def check_latency_alert(latencies_ms: list[float]) -> bool:
    if not latencies_ms:
        return False
    sorted_latencies = sorted(latencies_ms)
    n = len(sorted_latencies)
    p50 = sorted_latencies[int(n * 0.50)]
    p95 = sorted_latencies[int(n * 0.95)]
    p99 = sorted_latencies[min(int(n * 0.99), n - 1)]

    alerted = False
    if p99 > 1000:
        send_alert(f'P99 延迟过高: {p99:.0f}ms')
        alerted = True
    if p95 > 500:
        send_alert(f'P95 延迟过高: {p95:.0f}ms')
        alerted = True
    return alerted
```""",
    },
    "幂等接口把请求体哈希漏入时间戳": {
        "wrong": """\
```python
import hashlib, json, time

def make_idempotency_key(request_body: dict) -> str:
    # 把 timestamp 加入哈希，每次请求哈希值不同，幂等失效
    payload = {**request_body, 'ts': time.time()}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
```""",
        "correct": """\
```python
import hashlib, json

def make_idempotency_key(request_body: dict) -> str:
    # 只哈希业务字段，排除时间戳等变化字段
    stable_fields = {k: v for k, v in request_body.items()
                     if k not in ('timestamp', 'request_time', 'nonce')}
    return hashlib.sha256(
        json.dumps(stable_fields, sort_keys=True).encode()
    ).hexdigest()
```""",
    },
    "降级路径没有隔离慢依赖": {
        "wrong": """\
```typescript
async function getRecommendations(userId: string) {
    try {
        // 慢依赖没有超时控制，会阻塞整个请求线程池
        const recs = await recommendationService.get(userId);
        return recs;
    } catch {
        return [];   // 降级返回空，但已经等待了 30s
    }
}
```""",
        "correct": """\
```typescript
const TIMEOUT_MS = 200;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
    return Promise.race([
        promise,
        new Promise<never>((_, reject) =>
            setTimeout(() => reject(new Error('timeout')), ms)
        ),
    ]);
}

async function getRecommendations(userId: string) {
    try {
        // 超时快速失败，不阻塞主流程
        return await withTimeout(recommendationService.get(userId), TIMEOUT_MS);
    } catch (err) {
        metrics.increment('recommendations.fallback');
        return getCachedRecommendations(userId) ?? [];
    }
}
```""",
    },

    # ── 工程实践 ──────────────────────────────────────────────────────────────
    "单测只覆盖 happy path": {
        "wrong": """\
```python
def test_divide():
    assert divide(10, 2) == 5
    assert divide(9, 3) == 3
    # 只测正常情况，漏掉除以零、负数、浮点边界
```""",
        "correct": """\
```python
import pytest

def test_divide_happy_path():
    assert divide(10, 2) == 5

def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)

def test_divide_negative():
    assert divide(-10, 2) == -5

def test_divide_float_precision():
    assert abs(divide(1, 3) - 0.3333) < 1e-4

def test_divide_large_numbers():
    assert divide(10**18, 10**9) == 10**9
```""",
    },
    "mock 过度导致集成契约失真": {
        "wrong": """\
```typescript
// 把 DB 层完全 mock，测试只验证了自己写的假数据
jest.mock('../db', () => ({
    findUser: jest.fn().mockResolvedValue({ id: 1, name: 'Alice', role: 'admin' }),
}));

test('getUser returns admin', async () => {
    const user = await getUser(1);
    expect(user.role).toBe('admin');  // 只是验证了 mock 的返回值
});
```""",
        "correct": """\
```typescript
// 使用真实的测试数据库（内存 SQLite 或 testcontainers）
import { createTestDb } from '../test-utils/db';

let db: TestDatabase;

beforeEach(async () => {
    db = await createTestDb();
    await db.seed({ users: [{ id: 1, name: 'Alice', role: 'admin' }] });
});

afterEach(() => db.cleanup());

test('getUser returns correct role from real db', async () => {
    const user = await getUser(1, db);
    expect(user.role).toBe('admin');   // 验证真实数据路径
});
```""",
    },
    "类型守卫没有复用导致分支漂移": {
        "wrong": """\
```typescript
// 在 A 组件里写一次类型守卫
function ComponentA({ data }: { data: Cat | Dog }) {
    if ('meow' in data) {          // 内联判断，无法复用
        return <CatView cat={data} />;
    }
    return <DogView dog={data} />;
}

// B 组件复制了不同的判断逻辑，两处定义漂移
function ComponentB({ data }: { data: Cat | Dog }) {
    if (data.type === 'cat') {     // 与 A 的判断方式不一致
        return <CatIcon />;
    }
    return <DogIcon />;
}
```""",
        "correct": """\
```typescript
// 集中定义类型守卫，全局复用
function isCat(animal: Cat | Dog): animal is Cat {
    return 'meow' in animal;
}

function ComponentA({ data }: { data: Cat | Dog }) {
    if (isCat(data)) return <CatView cat={data} />;
    return <DogView dog={data} />;
}

function ComponentB({ data }: { data: Cat | Dog }) {
    if (isCat(data)) return <CatIcon />;
    return <DogIcon />;
}
```""",
    },
    "CI 缓存键遗漏 lockfile": {
        "wrong": """\
```python
# .github/workflows/ci.yml 等效逻辑（用 Python 描述）
cache_key = f'pip-{hash(open("requirements.txt").read())}'
# 漏掉 requirements.txt.lock / poetry.lock
# lockfile 变更后依然命中旧缓存，安装了旧版本依赖
```""",
        "correct": """\
```python
import hashlib, pathlib

def compute_cache_key() -> str:
    files = [
        'requirements.txt',
        'requirements.lock',   # 包含精确版本的锁文件
    ]
    h = hashlib.sha256()
    for f in files:
        p = pathlib.Path(f)
        if p.exists():
            h.update(p.read_bytes())
    return f'pip-{h.hexdigest()[:16]}'

# CI YAML 等效
# key: pip-${{ hashFiles('requirements.txt', 'requirements.lock') }}
```""",
    },
    "日志结构化字段命名不一致": {
        "wrong": """\
```python
import logging, json

# 模块 A
logger.info(json.dumps({'userId': user_id, 'action': 'login'}))

# 模块 B（同一系统，字段名不同）
logger.info(json.dumps({'user_id': user_id, 'event': 'login'}))

# Kibana / Grafana 查询时两套字段，聚合和告警规则重复维护
```""",
        "correct": """\
```python
import structlog

log = structlog.get_logger()

# 统一用结构化日志库，字段命名遵守团队规范
log.info('user.login', user_id=user_id, ip=request.remote_addr)

# 配置全局处理器，自动注入 service、env、trace_id
# 所有模块输出的字段命名保持一致，可直接在 Grafana 聚合
```""",
    },
    "代码评审漏看回滚路径": {
        "wrong": """\
```typescript
// PR 只审查了新功能代码，没有关注回滚方案
async function migrateUserData(batchSize = 1000) {
    const users = await db.query('SELECT * FROM users WHERE migrated = false LIMIT ?', [batchSize]);
    for (const user of users) {
        await transformAndSave(user);   // 若中途失败，已迁移的数据不可逆
        await db.query('UPDATE users SET migrated = true WHERE id = ?', [user.id]);
    }
}
```""",
        "correct": """\
```typescript
async function migrateUserData(batchSize = 1000) {
    const users = await db.query(
        'SELECT * FROM users WHERE migrated = false LIMIT ?', [batchSize]
    );
    // 使用事务：要么全部成功，要么全部回滚
    await db.transaction(async (trx) => {
        for (const user of users) {
            await transformAndSave(user, trx);
            await trx.query('UPDATE users SET migrated = true WHERE id = ?', [user.id]);
        }
    });
}
// Review checklist 应包含：
// [ ] 失败时数据状态是否可恢复
// [ ] 是否有对应的回滚迁移脚本
```""",
    },
    "异步任务测试没有等待队列排空": {
        "wrong": """\
```python
from myapp.tasks import send_welcome_email
from myapp.models import User

def test_register_sends_email(client, mailoutbox):
    client.post('/register', {'email': 'a@b.com', 'password': 'secret'})
    # 任务是异步的，邮件可能还没发出
    assert len(mailoutbox) == 1   # 偶发失败（竞态条件）
```""",
        "correct": """\
```python
from unittest.mock import patch
from myapp.tasks import send_welcome_email

def test_register_sends_email(client, mailoutbox):
    # 方案 1：在测试环境把 Celery 配置为 ALWAYS_EAGER，同步执行
    with patch('myapp.tasks.celery.conf.task_always_eager', True):
        client.post('/register', {'email': 'a@b.com', 'password': 'secret'})
    assert len(mailoutbox) == 1

    # 方案 2：直接测试 task 函数，不依赖 worker
    # send_welcome_email('a@b.com')
    # assert len(mailoutbox) == 1
```""",
    },
    "错误处理中吞掉原始异常": {
        "wrong": """\
```python
def load_config(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        # 把原始异常吞掉，调用方只看到通用消息，无法调试
        raise RuntimeError('配置加载失败')
```""",
        "correct": """\
```python
def load_config(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise RuntimeError(f'配置文件不存在: {path}') from e   # 保留原始异常链
    except json.JSONDecodeError as e:
        raise RuntimeError(f'配置文件格式错误: {path}') from e
```""",
    },
    "正则替换脚本没有 dry-run": {
        "wrong": """\
```python
import re, pathlib

def replace_in_codebase(pattern, replacement, root='.'):
    for path in pathlib.Path(root).rglob('*.py'):
        content = path.read_text()
        new_content = re.sub(pattern, replacement, content)
        path.write_text(new_content)   # 直接写入，无确认，无备份

replace_in_codebase(r'oldFunc', 'newFunc', '.')
```""",
        "correct": """\
```python
import re, pathlib

def replace_in_codebase(pattern, replacement, root='.', dry_run=True):
    changed = []
    for path in pathlib.Path(root).rglob('*.py'):
        content = path.read_text()
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            changed.append(path)
            if dry_run:
                print(f'[dry-run] 会修改: {path}')
            else:
                path.write_text(new_content)

    print(f'共 {len(changed)} 个文件{"将被" if dry_run else "已"}修改')
    return changed

# 先 dry-run 确认范围，再执行
replace_in_codebase(r'oldFunc', 'newFunc', '.', dry_run=True)
# replace_in_codebase(r'oldFunc', 'newFunc', '.', dry_run=False)
```""",
    },
    "重构公共函数后调用方语义变窄": {
        "wrong": """\
```typescript
// 重构前：formatDate 接受任意格式字符串
function formatDate(date: Date, format: string): string {
    return dayjs(date).format(format);
}

// 重构后：只支持预设枚举，调用方传自定义格式会静默产生错误输出
type DateFormat = 'short' | 'long';
function formatDate(date: Date, format: DateFormat): string {
    const formats = { short: 'MM/DD', long: 'YYYY-MM-DD HH:mm' };
    return dayjs(date).format(formats[format]);
}

// 旧调用方：formatDate(d, 'DD-MM-YYYY') → TypeScript 报错或行为改变
```""",
        "correct": """\
```typescript
type DateFormat = 'short' | 'long';

// 重构时保留旧签名作为重载，或提供迁移路径
function formatDate(date: Date, format: DateFormat): string;
function formatDate(date: Date, format: string): string;
function formatDate(date: Date, format: DateFormat | string): string {
    const presets: Record<DateFormat, string> = {
        short: 'MM/DD',
        long:  'YYYY-MM-DD HH:mm',
    };
    const pattern = (format in presets)
        ? presets[format as DateFormat]
        : format;
    return dayjs(date).format(pattern);
}
// 在下一个主版本才移除自定义格式支持
```""",
    },
}


def build_mistakes(categories: dict[str, Category], tags: dict[str, Tag], now: datetime) -> list[Mistake]:
    topic_pool = {
        "算法": [
            ("两数之和哈希表更新顺序", ["算法", "数组", "哈希"], "python"),
            ("链表反转丢失 next 指针", ["算法", "链表"], "python"),
            ("二叉树层序遍历队列边界", ["算法", "树"], "typescript"),
            ("动态规划状态转移漏初始化", ["算法", "动态规划"], "python"),
            ("滑动窗口收缩条件过早", ["算法", "数组", "哈希"], "javascript"),
            ("递归返回值覆盖子问题结果", ["算法", "树"], "python"),
            ("双指针去重跳过有效元素", ["算法", "数组"], "typescript"),
            ("前缀和下标偏移一位", ["算法", "数组", "哈希"], "python"),
            ("拓扑排序入度更新遗漏", ["算法", "哈希"], "typescript"),
            ("区间合并排序键选错", ["算法", "数组"], "python"),
        ],
        "前端": [
            ("React effect 依赖数组漏填", ["react", "javascript"], "javascript"),
            ("React key 使用数组下标导致复用错乱", ["react", "typescript"], "typescript"),
            ("受控输入 value 与 onChange 不匹配", ["react", "javascript"], "javascript"),
            ("CSS flex 子项收缩导致按钮溢出", ["react", "typescript"], "typescript"),
            ("Promise 链异常没有返回", ["javascript", "异步"], "javascript"),
            ("闭包读取旧状态导致计数跳变", ["javascript", "闭包", "react"], "javascript"),
            ("TypeScript props 可选字段未收窄", ["typescript", "类型系统", "react"], "typescript"),
            ("列表筛选条件大小写不一致", ["react", "typescript", "测试"], "typescript"),
            ("正则校验把全局标记状态带入表单", ["javascript", "测试"], "javascript"),
            ("异步请求取消后仍然 setState", ["react", "异步"], "typescript"),
        ],
        "Python": [
            ("Python 可变默认参数复用", ["python", "测试"], "python"),
            ("生成器耗尽后重复遍历为空", ["python"], "python"),
            ("字典遍历时删除键触发运行时错误", ["python", "哈希"], "python"),
            ("asyncio gather 异常传播误判", ["python", "异步"], "python"),
            ("闭包 late binding 捕获循环变量", ["python", "闭包"], "python"),
            ("装饰器没有保留函数元信息", ["python", "设计模式"], "python"),
            ("列表切片浅拷贝误改嵌套对象", ["python", "数组"], "python"),
            ("上下文管理器异常吞掉返回值", ["python", "测试"], "python"),
            ("正则分组贪婪匹配吞掉边界", ["python", "测试"], "python"),
            ("类型注解 Optional 分支未处理", ["python", "类型系统"], "python"),
        ],
        "数据库": [
            ("SQL JOIN 条件写在 WHERE 导致行丢失", ["sql"], "sql"),
            ("索引最左前缀没有命中", ["sql", "索引"], "sql"),
            ("事务隔离级别误读不可重复读", ["sql", "事务"], "sql"),
            ("分页 offset 大导致慢查询", ["sql", "索引"], "sql"),
            ("聚合 HAVING 与 WHERE 混用", ["sql"], "sql"),
            ("唯一约束冲突重试不幂等", ["sql", "事务", "测试"], "sql"),
            ("N+1 查询隐藏在序列化层", ["sql", "索引"], "python"),
            ("迁移脚本默认值没有回填历史数据", ["sql", "测试"], "sql"),
            ("锁等待超时没有回滚事务", ["sql", "事务"], "sql"),
            ("JSON 字段查询没有表达式索引", ["sql", "索引"], "sql"),
        ],
        "系统设计": [
            ("缓存穿透没有空值缓存", ["设计模式", "测试"], "python"),
            ("限流 key 维度选错导致误伤租户", ["设计模式"], "typescript"),
            ("消息队列重试缺少幂等键", ["异步", "设计模式"], "python"),
            ("读写分离延迟导致读己之写失败", ["事务", "设计模式"], "sql"),
            ("分布式锁过期时间覆盖长任务", ["异步", "设计模式"], "python"),
            ("接口版本兼容字段直接删除", ["typescript", "设计模式"], "typescript"),
            ("批处理任务没有断点续跑", ["测试", "设计模式"], "python"),
            ("告警阈值只看均值漏掉长尾", ["测试"], "python"),
            ("幂等接口把请求体哈希漏入时间戳", ["哈希", "设计模式"], "python"),
            ("降级路径没有隔离慢依赖", ["异步", "设计模式"], "typescript"),
        ],
        "工程实践": [
            ("单测只覆盖 happy path", ["测试"], "python"),
            ("mock 过度导致集成契约失真", ["测试", "设计模式"], "typescript"),
            ("类型守卫没有复用导致分支漂移", ["typescript", "类型系统"], "typescript"),
            ("CI 缓存键遗漏 lockfile", ["测试"], "python"),
            ("日志结构化字段命名不一致", ["测试"], "python"),
            ("代码评审漏看回滚路径", ["设计模式", "测试"], "typescript"),
            ("异步任务测试没有等待队列排空", ["异步", "测试"], "python"),
            ("错误处理中吞掉原始异常", ["python", "测试"], "python"),
            ("正则替换脚本没有 dry-run", ["测试"], "python"),
            ("重构公共函数后调用方语义变窄", ["设计模式", "类型系统"], "typescript"),
        ],
    }

    statuses = (
        [MistakeStatus.NEW] * 10
        + [MistakeStatus.LEARNING] * 15
        + [MistakeStatus.REVIEWING] * 25
        + [MistakeStatus.MASTERED] * 10
    )
    mistakes: list[Mistake] = []

    for category_index, category_name in enumerate(CATEGORY_NAMES):
        for local_index, (title, tag_names, language) in enumerate(topic_pool[category_name]):
            index = category_index * 10 + local_index
            created_at = created_at_for(index, now)
            content = MISTAKE_CONTENT.get(title, {})
            narrative = MISTAKE_NARRATIVE.get(title, {})

            if index < 15:
                next_review_at = now - timedelta(days=1 + index % 9, hours=index % 6)
            elif index < 33:
                next_review_at = now + timedelta(days=1 + (index - 15) % 14, hours=index % 9)
            else:
                next_review_at = None

            review_age = max(0, (now - created_at).days)
            repetition = 0 if statuses[index] == MistakeStatus.NEW else min(8, 1 + index % 7)
            interval_days = 0 if statuses[index] == MistakeStatus.NEW else min(45, 1 + review_age // 3 + index % 5)
            ease_factor = round(max(1.3, min(5.0, 2.9 - (index % 11) * 0.08 + category_index * 0.07)), 2)

            mistakes.append(
                Mistake(
                    title=title,
                    stem_markdown=narrative.get("stem_markdown", f"复盘 `{title}`：指出错误原因，并写出更稳的实现或判断步骤。"),
                    wrong_answer_markdown=content.get("wrong", "直接套用上一次模板，忽略当前输入边界和运行时状态。"),
                    correct_answer_markdown=content.get("correct", "先列出不变量和边界条件，再用最小反例验证分支；必要时补一条回归测试。"),
                    error_reason_markdown=narrative.get("error_reason_markdown", "主要问题是把记忆中的套路当成当前题目的充分条件，没有验证关键约束。"),
                    language=language,
                    category=categories[category_name],
                    difficulty=1 + index % 5,
                    source="CodeRecall demo seed",
                    status=statuses[index],
                    tags=[tags[name] for name in tag_names],
                    review_count=0,
                    last_reviewed_at=None,
                    next_review_at=next_review_at,
                    ease_factor=ease_factor,
                    interval_days=interval_days,
                    repetition=repetition,
                    is_archived=False,
                    created_at=created_at,
                    updated_at=created_at,
                )
            )

    return mistakes


def daily_review_counts() -> list[int]:
    first_60 = []
    for index in range(60):
        if index % 6 == 0:
            count = 0
        elif index % 10 == 3:
            count = 4
        elif index % 4 == 0:
            count = 3
        elif index % 3 == 0:
            count = 2
        elif index % 2 == 0:
            count = 1
        else:
            count = 0
        first_60.append(count)

    last_30 = [7, 8, 10, 9, 11, 8, 12, 9, 10, 11, 8, 12, 9, 10, 7, 11, 12, 9, 10, 8, 11, 12, 10, 9, 11, 8, 12, 10, 11, 9]
    return first_60 + last_30


def review_time_for(day: datetime, count: int, slot: int, now: datetime) -> datetime:
    if day.date() == now.date():
        minutes_back = max(5, (count - slot) * 17)
        return now - timedelta(minutes=minutes_back)
    return day.replace(hour=8 + (slot * 2) % 12, minute=(slot * 13) % 60, second=0, microsecond=0)


def pick_mode(mode_counts: Counter[str]) -> str:
    for mode, quota in MODE_QUOTAS.items():
        if mode_counts[mode] < quota:
            return mode
    return "React"


def result_for(mistake_index: int, day_index: int, seen_for_mistake: int) -> ReviewResult:
    if mistake_index < 8 and day_index >= 60:
        pattern_by_index = {
            0: [ReviewResult.AGAIN, ReviewResult.AGAIN, ReviewResult.HARD, ReviewResult.AGAIN, ReviewResult.HARD],
            1: [ReviewResult.AGAIN, ReviewResult.HARD, ReviewResult.HARD, ReviewResult.GOOD],
            2: [ReviewResult.HARD, ReviewResult.AGAIN, ReviewResult.HARD, ReviewResult.GOOD],
            3: [ReviewResult.AGAIN, ReviewResult.HARD, ReviewResult.GOOD],
            4: [ReviewResult.HARD, ReviewResult.HARD, ReviewResult.GOOD],
            5: [ReviewResult.AGAIN, ReviewResult.GOOD, ReviewResult.HARD],
            6: [ReviewResult.HARD, ReviewResult.GOOD, ReviewResult.GOOD],
            7: [ReviewResult.AGAIN, ReviewResult.HARD, ReviewResult.EASY],
        }
        pattern = pattern_by_index[mistake_index]
        return pattern[seen_for_mistake % len(pattern)]

    if day_index < 60:
        return [ReviewResult.GOOD, ReviewResult.EASY, ReviewResult.GOOD, ReviewResult.HARD][(mistake_index + day_index) % 4]

    return [ReviewResult.GOOD, ReviewResult.GOOD, ReviewResult.EASY, ReviewResult.HARD, ReviewResult.GOOD][
        (mistake_index + day_index + seen_for_mistake) % 5
    ]


def build_review_logs(mistakes: list[Mistake], now: datetime) -> list[ReviewLog]:
    mode_to_indices = {
        "React": [i for i, mistake in enumerate(mistakes) if any(tag.name == "react" for tag in mistake.tags)],
        "Async": [i for i, mistake in enumerate(mistakes) if any(tag.name == "异步" for tag in mistake.tags)],
        "Regex": [8, 28, 58, 17, 27, 47],
        "CSS": [13, 11, 19, 56, 57, 59],
    }
    fallback_indices = list(range(len(mistakes)))
    mode_counts: Counter[str] = Counter()
    mistake_counts: Counter[int] = Counter()
    mode_cursors: Counter[str] = Counter()
    logs: list[ReviewLog] = []
    counts = daily_review_counts()
    start_day = (now - timedelta(days=89)).replace(hour=0, minute=0, second=0, microsecond=0)

    for day_index, count in enumerate(counts):
        day = start_day + timedelta(days=day_index)
        for slot in range(count):
            mode = pick_mode(mode_counts)
            candidates = mode_to_indices.get(mode) or fallback_indices

            if day_index >= 60 and slot < 4:
                mistake_index = (day_index + slot) % 8
            else:
                cursor = mode_cursors[mode]
                mistake_index = candidates[cursor % len(candidates)]
                mode_cursors[mode] += 1

            mistake = mistakes[mistake_index]
            shown_at = review_time_for(day, count, slot, now)
            result = result_for(mistake_index, day_index, mistake_counts[mistake_index])
            old_interval = mistake.interval_days if mistake_counts[mistake_index] else max(0, mistake.interval_days - 1)
            new_interval = 1 if result == ReviewResult.AGAIN else max(1, old_interval + (1 if result == ReviewResult.HARD else 3))
            old_ease = max(1.3, mistake.ease_factor - 0.03)
            ease_delta = {
                ReviewResult.AGAIN: -0.28,
                ReviewResult.HARD: -0.12,
                ReviewResult.GOOD: 0.04,
                ReviewResult.EASY: 0.14,
            }[result]
            new_ease = round(max(1.3, min(5.0, old_ease + ease_delta)), 2)

            logs.append(
                ReviewLog(
                    mistake=mistake,
                    session_id=None,
                    review_mode=mode,
                    user_result=result,
                    shown_at=shown_at,
                    answered_at=shown_at + timedelta(seconds=35 + (slot * 17) % 90),
                    old_interval_days=old_interval,
                    new_interval_days=new_interval,
                    old_ease_factor=round(old_ease, 2),
                    new_ease_factor=new_ease,
                    time_spent_ms=26000 + ((day_index + slot) % 9) * 7000,
                    note=f"{mode} demo distribution",
                )
            )
            mode_counts[mode] += 1
            mistake_counts[mistake_index] += 1

    return logs


def refresh_mistake_review_fields(mistakes: list[Mistake], logs: list[ReviewLog], now: datetime) -> None:
    logs_by_mistake: dict[Mistake, list[ReviewLog]] = defaultdict(list)
    for log in logs:
        logs_by_mistake[log.mistake].append(log)

    for mistake in mistakes:
        mistake_logs = sorted(logs_by_mistake.get(mistake, []), key=lambda item: item.shown_at)
        mistake.review_count = len(mistake_logs)
        if mistake_logs:
            last = mistake_logs[-1]
            mistake.last_reviewed_at = last.shown_at
            mistake.updated_at = max(mistake.updated_at, last.shown_at)
            mistake.ease_factor = float(last.new_ease_factor or mistake.ease_factor)
            mistake.interval_days = int(last.new_interval_days or mistake.interval_days)

        if mistake.status == MistakeStatus.NEW:
            mistake.repetition = 0
            mistake.interval_days = 0
            mistake.ease_factor = min(5.0, max(1.3, mistake.ease_factor))
        elif mistake.status == MistakeStatus.LEARNING:
            mistake.repetition = max(1, min(mistake.repetition, 2))
        elif mistake.status == MistakeStatus.REVIEWING:
            mistake.repetition = max(3, mistake.repetition)
        else:
            mistake.repetition = max(5, mistake.repetition)


def assert_targets(session, now: datetime) -> None:
    mistake_count = session.scalar(func.count(Mistake.id))
    log_count = session.scalar(func.count(ReviewLog.id))
    if mistake_count != 60:
        raise RuntimeError(f"expected 60 mistakes, got {mistake_count}")
    if not 360 <= int(log_count or 0) <= 520:
        raise RuntimeError(f"expected 360-520 review logs, got {log_count}")

    status_counts = dict(session.query(Mistake.status, func.count()).group_by(Mistake.status).all())
    expected = {
        MistakeStatus.NEW: 10,
        MistakeStatus.LEARNING: 15,
        MistakeStatus.REVIEWING: 25,
        MistakeStatus.MASTERED: 10,
    }
    if status_counts != expected:
        raise RuntimeError(f"unexpected status distribution: {status_counts}")

    due_count = session.scalar(
        select(func.count(Mistake.id)).where(Mistake.next_review_at.is_not(None), Mistake.next_review_at <= now)
    )
    future_count = session.scalar(
        select(func.count(Mistake.id)).where(Mistake.next_review_at.is_not(None), Mistake.next_review_at > now)
    )
    if not 12 <= int(due_count or 0) <= 18:
        raise RuntimeError(f"expected 12-18 due mistakes, got {due_count}")
    if not 15 <= int(future_count or 0) <= 20:
        raise RuntimeError(f"expected 15-20 future mistakes, got {future_count}")


def main() -> int:
    now = utc_now_naive()
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    try:
        clear_tables(session)

        categories = {
            name: Category(
                name=name,
                description=f"CodeRecall demo category: {name}",
                sort_order=index,
                created_at=now,
                updated_at=now,
            )
            for index, name in enumerate(CATEGORY_NAMES)
        }
        tags = {name: Tag(name=name, created_at=now, updated_at=now) for name in TAG_NAMES}
        session.add_all(categories.values())
        session.add_all(tags.values())
        session.flush()

        mistakes = build_mistakes(categories, tags, now)
        session.add_all(mistakes)
        session.flush()

        review_logs = build_review_logs(mistakes, now)
        refresh_mistake_review_fields(mistakes, review_logs, now)
        session.add_all(review_logs)
        session.commit()

        assert_targets(session, now)

        print("seeded_demo_data")
        print(f"categories={session.scalar(func.count(Category.id))}")
        print(f"tags={session.scalar(func.count(Tag.id))}")
        print(f"mistakes={session.scalar(func.count(Mistake.id))}")
        print(f"review_logs={session.scalar(func.count(ReviewLog.id))}")
        print(
            "due="
            f"{session.scalar(select(func.count(Mistake.id)).where(Mistake.next_review_at.is_not(None), Mistake.next_review_at <= now))} "
            "future="
            f"{session.scalar(select(func.count(Mistake.id)).where(Mistake.next_review_at.is_not(None), Mistake.next_review_at > now))}"
        )
        print(f"database_url={session.bind.url}")
        return 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
