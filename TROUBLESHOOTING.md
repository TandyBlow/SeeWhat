# 树可视化不显示问题排查清单

## 问题现象
- 主页看不到树
- 退出登录按钮又出现了（但这个按钮应该已经被移除）
- 导航栏滚动动画是新的

## 可能原因分析

### 1. Vercel 环境变量未配置 ⚠️ 最可能
**症状**: 前端无法连接到后端 API
**检查方法**:
1. 打开浏览器开发者工具 (F12)
2. 查看 Console 标签页，是否有 "Failed to load tree skeleton:" 错误
3. 查看 Network 标签页，刷新页面，查找对 `generate-tree-skeleton` 的请求
   - 如果请求地址是 `http://localhost:7860/...` → 环境变量未配置
   - 如果请求地址是 `https://tandyblow-seewhat.hf.space/...` → 环境变量已配置

**解决方法**:
访问 Vercel 项目设置 → Environment Variables，添加：
```
VITE_BACKEND_URL=https://tandyblow-seewhat.hf.space
```
然后触发重新部署（Deployments → 最新部署 → Redeploy）

### 2. 你不在主页
**症状**: 有 activeNode，所以显示编辑器而不是树
**检查方法**: 
- 查看 URL，是否包含节点 ID
- 查看面包屑导航，是否在某个节点下

**解决方法**:
点击旋钮返回主页，或点击面包屑最左侧的根节点

### 3. 后端未部署或环境变量未配置
**症状**: 后端 API 返回 500 错误
**检查方法**:
访问 https://tandyblow-seewhat.hf.space/docs 查看 API 文档是否可访问

**解决方法**:
在 HF Spaces 设置 → Repository secrets 添加：
```
SUPABASE_URL=https://uqblmypxkljuqwtzsrzy.supabase.co
SUPABASE_SERVICE_KEY=<你的 service key>
```

### 4. 你的账号没有节点数据
**症状**: 后端返回 404 "No tree data found"
**检查方法**: 
在 Supabase 数据库中查询你的 user_id 是否有 nodes 数据

**解决方法**:
创建一些节点后再查看树

## 关于"退出登录按钮又回来了"

这个描述有些混淆。让我澄清：

1. **编辑器中的退出登录按钮** - 已在提交 240f786 中移除（这是正确的）
2. **主页的退出登录流程** - 通过旋钮长按触发，这是正常的功能

如果你看到的是编辑器中有退出登录按钮，说明 Vercel 部署的不是最新代码。

## 立即诊断步骤

1. **打开线上网站** (你的 Vercel 地址)
2. **按 F12 打开开发者工具**
3. **切换到 Console 标签页**
4. **刷新页面**
5. **查看是否有红色错误信息**
6. **切换到 Network 标签页**
7. **查找 `generate-tree-skeleton` 请求**
8. **查看请求的完整 URL**

把这些信息告诉我，我就能准确定位问题。
