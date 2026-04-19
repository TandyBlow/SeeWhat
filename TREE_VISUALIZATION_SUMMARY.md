# L-system Tree Visualization Generator

完整的知识树可视化骨架生成系统实现。

## 已完成的文件

### 核心实现
- ✅ `backend/tree_generator.py` - L-system 生成器主实现（311 行）
- ✅ `backend/main.py` - 添加了 `/generate-tree/{user_id}` API 端点
- ✅ `supabase/migrations/20260418000000_add_tree_skeletons.sql` - 数据库表迁移

### 配置文件
- ✅ `backend/.env.example` - 环境变量模板
- ✅ `backend/requirements.txt` - 添加了 Pillow, numpy, pytest 等依赖

### 测试文件
- ✅ `backend/test_tree_generator.py` - 命令行测试脚本
- ✅ `backend/test_tree_generator_unit.py` - 单元测试（8 个测试类）
- ✅ `backend/test_tree_generator_integration.py` - 集成测试（mock Supabase）

### 文档
- ✅ `backend/TREE_GENERATOR.md` - 完整使用文档
- ✅ `backend/EXAMPLES.md` - API 调用示例（Python/JS/cURL）
- ✅ `backend/setup_tree_generator.sh` - 自动化设置脚本

## 核心功能

### L-system 规则生成
根据子节点数量动态生成分形规则：
- 0 个子节点（叶子）: `F → F`
- 1 个子节点: `F → F[+F]`
- 2 个子节点: `F → F[+F][-F]`
- 3 个子节点: `F → F[+F][F][-F]`
- n 个子节点: 均匀分布在 ±25° 范围

### 确定性随机化
使用 `hash(node_id) + branch_index` 作为随机种子，确保：
- 同一棵树每次生成形态一致
- 不同树之间形态各异
- 角度扰动范围：±5°

### 视觉参数
- 画布尺寸: 512×512
- 起点: (256, 480) 底部中心
- 初始角度: 90° 向上
- 长度衰减: 每段 × 0.7
- 线条粗细: `max(1, 8 - depth)`

## 下一步操作

需要手动完成以下配置（已记录在任务列表）：

1. **创建 Storage Bucket** (#11)
   - 在 Supabase Dashboard > Storage
   - 创建名为 `tree-assets` 的 Public bucket

2. **配置环境变量** (#12)
   - 复制 `backend/.env.example` 为 `backend/.env`
   - 填入 `SUPABASE_URL` 和 `SUPABASE_SERVICE_KEY`

3. **运行数据库迁移** (#13)
   - 在 Supabase SQL Editor 执行迁移文件
   - 或使用 `supabase db push`

4. **安装依赖** (#14)
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

5. **测试** (#15)
   ```bash
   # 单元测试
   pytest test_tree_generator_unit.py -v
   
   # 命令行测试
   python test_tree_generator.py <user_id>
   
   # API 测试
   uvicorn main:app --reload
   curl -X POST http://localhost:8000/generate-tree/<user_id>
   ```

## 快速开始

运行自动化设置脚本：
```bash
cd backend
./setup_tree_generator.sh
```

或查看详细文档：
- 使用说明: `backend/TREE_GENERATOR.md`
- 代码示例: `backend/EXAMPLES.md`
