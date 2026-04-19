# Tree Visualization Generator

L-system 知识树骨架生成器，根据用户的知识树结构生成分形树可视化。

## 功能

- 从 Supabase 读取用户的完整知识树数据（nodes + edges）
- 根据节点层级深度和子节点数量动态生成 L-system 规则
- 使用确定性随机扰动（基于节点 UUID）生成独特但一致的树形态
- 输出 JSON 坐标数据和 PNG 线稿图
- 自动上传到 Supabase Storage 并保存元数据

## 设置步骤

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入 Supabase 凭证：

```bash
cp .env.example .env
```

编辑 `.env`：
```
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

在 Supabase Dashboard 获取：
- URL: Project Settings > API > Project URL
- Service Key: Project Settings > API > service_role key（注意保密！）

### 3. 运行数据库迁移

在 Supabase Dashboard 的 SQL Editor 中执行：

```bash
cat supabase/migrations/20260418000000_add_tree_skeletons.sql
```

或使用 Supabase CLI：
```bash
supabase db push
```

### 4. 创建 Storage Bucket

在 Supabase Dashboard:
1. 进入 Storage 页面
2. 创建新 bucket: `tree-assets`
3. 设置为 Public（允许公开访问生成的 PNG）

## 使用方法

### 方式 1: 命令行测试脚本

```bash
python test_tree_generator.py <user_id>
```

示例：
```bash
python test_tree_generator.py 550e8400-e29b-41d4-a716-446655440000
```

### 方式 2: FastAPI 端点

启动服务器：
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 7860
```

发送请求：
```bash
curl -X POST http://localhost:7860/generate-tree/<user_id>
```

响应示例：
```json
{
  "png_url": "https://xxx.supabase.co/storage/v1/object/public/tree-assets/user-id/20260418_123456.png"
}
```

### 方式 3: Python 代码调用

```python
from tree_generator import generate_tree_visualization

user_id = "550e8400-e29b-41d4-a716-446655440000"
png_url = generate_tree_visualization(user_id)
print(f"Generated tree: {png_url}")
```

## L-system 规则说明

生成器根据每个节点的子节点数量动态生成 L-system 规则：

| 子节点数 | L-system 规则 | 说明 |
|---------|--------------|------|
| 0 (叶子) | `F → F` | 不分叉 |
| 1 | `F → F[+F]` | 单分支 |
| 2 | `F → F[+F][-F]` | 左右对称 |
| 3 | `F → F[+F][F][-F]` | 左中右 |
| n | `F → F[+F]...[+F][-F]...[-F]` | n 个分支均匀分布 |

### 参数

- **起点**: (256, 480) 画布底部中心
- **初始角度**: 90° (向上)
- **基础分叉角度**: ±25°
- **角度扰动**: ±5° (使用 `hash(node_id) + branch_index` 作为随机种子)
- **长度衰减**: 每段 × 0.7
- **线条粗细**: `max(1, 8 - depth)`
- **画布尺寸**: 512 × 512

## 输出格式

### skeleton_data (JSON)

```json
{
  "branches": [
    {
      "start": [256, 480],
      "end": [256, 400],
      "thickness": 8,
      "node_id": "550e8400-e29b-41d4-a716-446655440000",
      "depth": 0
    },
    ...
  ],
  "canvas_size": [512, 512]
}
```

### PNG 图像

- 512×512 白底黑线
- 线宽根据深度变化
- 自动上传到 `tree-assets/{user_id}/{timestamp}.png`

## 数据库表结构

### tree_skeletons

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | uuid | 主键 |
| owner_id | uuid | 用户 ID (外键到 auth.users) |
| skeleton_data | jsonb | 骨架坐标数据 |
| png_url | text | PNG 公开 URL |
| created_at | timestamptz | 创建时间 |

## 注意事项

1. **权限**: 使用 service_role key 绕过 RLS，确保不要泄露到前端
2. **性能**: 大型树（>100 节点）可能需要优化迭代次数
3. **存储**: 每个 PNG 约 50KB，注意 Storage 配额
4. **多根节点**: 当前仅处理第一个根节点，多根需要额外处理
5. **mastery_score**: 当前硬编码 0.5，后续需要从出题系统获取

## 故障排查

### 错误: "No tree data found for user"
- 检查 user_id 是否正确
- 确认该用户在 nodes 表中有数据
- 确认 is_deleted = false

### 错误: Storage upload failed
- 检查 `tree-assets` bucket 是否已创建
- 确认 bucket 权限设置正确
- 检查 SUPABASE_SERVICE_KEY 是否有效

### 错误: Database connection failed
- 检查 .env 文件中的 SUPABASE_URL 和 SUPABASE_SERVICE_KEY
- 确认网络连接正常
- 检查 Supabase 项目是否处于活跃状态
