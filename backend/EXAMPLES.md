# Tree Generator API Examples

## cURL Examples

### Generate tree for a user

```bash
curl -X POST http://localhost:7860/generate-tree/550e8400-e29b-41d4-a716-446655440000
```

Response:
```json
{
  "png_url": "https://xxx.supabase.co/storage/v1/object/public/tree-assets/550e8400-e29b-41d4-a716-446655440000/20260418_123456.png"
}
```

### Error responses

User not found:
```json
{
  "detail": "No tree data found for user 550e8400-e29b-41d4-a716-446655440000"
}
```

Server error:
```json
{
  "detail": "Storage upload failed: ..."
}
```

## Python Examples

### Basic usage

```python
from tree_generator import generate_tree_visualization

user_id = "550e8400-e29b-41d4-a716-446655440000"
png_url = generate_tree_visualization(user_id)
print(f"Tree generated: {png_url}")
```

### With error handling

```python
from tree_generator import generate_tree_visualization

try:
    png_url = generate_tree_visualization(user_id)
    print(f"Success: {png_url}")
except ValueError as e:
    print(f"User error: {e}")
except Exception as e:
    print(f"Server error: {e}")
```

### Fetch tree data only

```python
from tree_generator import fetch_user_tree

tree_data = fetch_user_tree(user_id)
for node in tree_data:
    print(f"{node['name']}: depth={node['depth']}, children={node['child_count']}")
```

### Generate skeleton without saving

```python
from tree_generator import fetch_user_tree, generate_lsystem_skeleton

tree_data = fetch_user_tree(user_id)
skeleton = generate_lsystem_skeleton(tree_data)

print(f"Generated {len(skeleton['branches'])} branches")
print(f"Canvas size: {skeleton['canvas_size']}")
```

### Render PNG locally

```python
from tree_generator import (
    fetch_user_tree,
    generate_lsystem_skeleton,
    render_skeleton_png
)

tree_data = fetch_user_tree(user_id)
skeleton = generate_lsystem_skeleton(tree_data)
png_bytes = render_skeleton_png(skeleton)

# Save to local file
with open("tree.png", "wb") as f:
    f.write(png_bytes.getvalue())
```

## JavaScript/TypeScript Examples

### Fetch from frontend

```typescript
async function generateTree(userId: string): Promise<string> {
  const response = await fetch(
    `http://localhost:7860/generate-tree/${userId}`,
    { method: 'POST' }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  const data = await response.json();
  return data.png_url;
}

// Usage
try {
  const pngUrl = await generateTree('550e8400-e29b-41d4-a716-446655440000');
  console.log('Tree generated:', pngUrl);
  
  // Display in img tag
  document.getElementById('tree-img').src = pngUrl;
} catch (error) {
  console.error('Failed to generate tree:', error);
}
```

### With loading state

```typescript
import { ref } from 'vue';

const isGenerating = ref(false);
const treeUrl = ref<string | null>(null);
const error = ref<string | null>(null);

async function generateTree(userId: string) {
  isGenerating.value = true;
  error.value = null;
  
  try {
    const response = await fetch(
      `http://localhost:7860/generate-tree/${userId}`,
      { method: 'POST' }
    );
    
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail);
    }
    
    const data = await response.json();
    treeUrl.value = data.png_url;
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Unknown error';
  } finally {
    isGenerating.value = false;
  }
}
```

## Batch Processing Example

Generate trees for multiple users:

```python
from tree_generator import generate_tree_visualization
import time

user_ids = [
    "550e8400-e29b-41d4-a716-446655440000",
    "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
]

results = []
for user_id in user_ids:
    try:
        png_url = generate_tree_visualization(user_id)
        results.append({"user_id": user_id, "status": "success", "url": png_url})
        print(f"✓ {user_id}: {png_url}")
    except Exception as e:
        results.append({"user_id": user_id, "status": "error", "error": str(e)})
        print(f"✗ {user_id}: {e}")
    
    time.sleep(0.5)  # Rate limiting

print(f"\nProcessed {len(results)} users")
print(f"Success: {sum(1 for r in results if r['status'] == 'success')}")
print(f"Failed: {sum(1 for r in results if r['status'] == 'error')}")
```

## Testing Examples

### Test with mock data

```python
import pytest
from unittest.mock import patch, Mock

def test_generate_tree():
    with patch('tree_generator.supabase') as mock_supabase:
        # Mock nodes
        nodes_mock = Mock()
        nodes_mock.data = [
            {
                "id": "root",
                "name": "Root",
                "depth": 0,
                "parent_id_cache": None,
                "content": {}
            }
        ]
        
        # Mock edges
        edges_mock = Mock()
        edges_mock.data = []
        
        # Setup mocks
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = nodes_mock
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value = edges_mock
        
        # Mock storage
        storage_mock = Mock()
        storage_mock.upload.return_value = {}
        storage_mock.get_public_url.return_value = "https://example.com/test.png"
        mock_supabase.storage.from_.return_value = storage_mock
        
        # Mock table insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value = Mock()
        
        from tree_generator import generate_tree_visualization
        result = generate_tree_visualization("test-user")
        
        assert result == "https://example.com/test.png"
```
