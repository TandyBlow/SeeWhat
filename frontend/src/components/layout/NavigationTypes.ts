import { NAV_ROW_H, NAV_ROW_GAP } from '../../constants/app'
import type { NodeRecord } from '../../types/node'

export interface NavItem {
  id: string
  name: string
  isOfficial: boolean
  action?: () => void
  nodeData?: NodeRecord
}

export interface ScrollEntry {
  direction: 'up' | 'down'
}

export type NavPhase = 'idle' | 'sinking' | 'sliding-out' | 'sliding-in-prep' | 'sliding-in' | 'rising'

// Page navigation animation durations (mirrors breadcrumbs: sink → slide-out → slide-in → rise)
export const NAV_SINK_MS = 240
export const NAV_SLIDE_MS = 280
export const NAV_RISE_MS = 240

export const ROW_STEP = NAV_ROW_H + NAV_ROW_GAP
