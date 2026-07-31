export interface DemoAccount {
  username: string
  label: string
  desc: string
}

export interface ProfileData {
  nodeCount: number
  profileTextLength: number
  hash: string
  hashShort: string
  profileText: string
  nodes: { name: string; contentPreview: string; hasContent: boolean }[]
}

export const DEMO_PASSWORD = 'demo123'

export const DEMO_ACCOUNTS: DemoAccount[] = [
  { username: 'alex_gamedev', label: '游戏设计爱好者', desc: '18节点 · 游戏引擎/关卡设计/AI' },
  { username: 'jamie_fullstack', label: '全栈开发者', desc: '17节点 · React/Node.js/DevOps' },
  { username: 'emma_piano', label: '钢琴学生', desc: '16节点 · 巴赫/肖邦/踏板技法' },
  { username: 'yuki_japanese', label: '日语学习者', desc: '18节点 · N2语法/动漫日语/文化' },
]
